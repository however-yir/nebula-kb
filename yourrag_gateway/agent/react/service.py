"""ReAct Agent Service — adapter bridging P1's ReAct into the unified gateway.

This wraps P1's ReAct graph as an alternative to P3's Canvas DSL.
When `agent_mode = "react"`, this service is used; otherwise Canvas takes over.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from yourrag_gateway.api.schemas import AgentStep, ChatRequest, ChatResponse, SearchHit
from yourrag_gateway.core.settings import YourRAGSettings
from yourrag_gateway.tools.executor import get_tool_executor

logger = logging.getLogger(__name__)


class _FallbackLLM:
    """Degraded LLM when no provider is available."""

    def invoke(self, _: str):
        fallback = {
            "thought": "Fallback mode — no LLM available.",
            "action": "finish",
            "action_input": {},
            "answer": "当前运行于轻量降级模式，建议在完整依赖环境下获得更高质量回答。",
        }
        return type("_Resp", (), {"content": json.dumps(fallback, ensure_ascii=False)})()


class AgentState(TypedDict, total=False):
    user_id: str
    session_id: str
    question: str
    department: str | None
    step: int
    action: str
    action_input: dict[str, Any]
    thought: str
    answer_candidate: str
    final_answer: str
    retrieved_preview: list[SearchHit]
    trace: list[AgentStep]
    observations: list[str]
    context: str


class ReActAgentService:
    """Lightweight ReAct agent that uses YourRAG Gateway's tool executor and RAG search."""

    def __init__(self, settings: YourRAGSettings | None = None) -> None:
        self.settings = settings or YourRAGSettings()
        self.llm = self._init_llm()

    def _init_llm(self):
        """Try to initialize an LLM based on configured provider."""
        provider = self.settings.llm_provider
        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(model=self.settings.ollama_model, base_url=self.settings.ollama_base_url, temperature=0.2)
            except Exception as exc:
                logger.warning("ChatOllama unavailable, using fallback: %s", exc)
                return _FallbackLLM()
        elif provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key, temperature=0.2)
            except Exception as exc:
                logger.warning("ChatOpenAI unavailable, using fallback: %s", exc)
                return _FallbackLLM()
        elif provider == "litellm":
            try:
                import litellm  # noqa: F401
                return _LiteLLMAdapter(self.settings)
            except Exception as exc:
                logger.warning("LiteLLM unavailable, using fallback: %s", exc)
                return _FallbackLLM()
        return _FallbackLLM()

    def _extract_json(self, content: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return {"thought": "Parse failure", "action": "finish", "action_input": {}, "answer": content.strip()}
        try:
            parsed = json.loads(match.group(0))
            parsed.setdefault("thought", "")
            parsed.setdefault("action", "finish")
            parsed.setdefault("action_input", {})
            parsed.setdefault("answer", "")
            return parsed
        except json.JSONDecodeError:
            return {"thought": "JSON decode error", "action": "finish", "action_input": {}, "answer": content.strip()}

    def run(self, request: ChatRequest) -> ChatResponse:
        question = request.message
        session_id = request.session_id or "default"

        # Initial RAG search
        context = self._initial_search(question, request.department)

        state: AgentState = {
            "user_id": request.user_id,
            "session_id": session_id,
            "question": question,
            "department": request.department,
            "step": 0,
            "trace": [],
            "observations": [],
            "context": context,
            "retrieved_preview": [],
        }

        # ReAct loop
        for _ in range(self.settings.max_agent_steps):
            state = self._reason(state)
            if state.get("action") == "finish" or state.get("step", 0) > self.settings.max_agent_steps:
                break
            state = self._act(state)

        # Finalize
        if not state.get("final_answer"):
            state["final_answer"] = state.get("answer_candidate") or "未能生成答案，请重试。"

        return ChatResponse(
            session_id=session_id,
            answer=state["final_answer"],
            trace=state.get("trace", []),
            retrieval_preview=state.get("retrieved_preview", []),
            route="react",
        )

    def _initial_search(self, query: str, department: str | None) -> str:
        try:
            from yourrag_gateway.api.routes import rag_search
            from yourrag_gateway.api.schemas import SearchRequest
            result = rag_search(SearchRequest(query=query, department=department))
            return "\n".join(hit.content[:300] for hit in result.hits)
        except Exception:
            return ""

    def _reason(self, state: AgentState) -> AgentState:
        tool_executor = get_tool_executor(self.settings)
        tool_names = list(tool_executor._registry.keys())
        prompt = f"""You are a ReAct agent. Decide one next step.

Available actions: search_docs, {', '.join(tool_names)}, finish

Question: {state['question']}
Context: {state.get('context', '')}
Previous observations: {state.get('observations', [])}
Current step: {state.get('step', 0)}

Return ONLY JSON:
{{"thought": "reason briefly", "action": "one action from list", "action_input": {{"key": "value"}}, "answer": "only fill when action=finish"}}"""

        content = self.llm.invoke(prompt).content
        parsed = self._extract_json(content)
        state["thought"] = parsed["thought"]
        state["action"] = parsed["action"]
        state["action_input"] = parsed["action_input"]
        state["answer_candidate"] = parsed["answer"]
        return state

    def _act(self, state: AgentState) -> AgentState:
        action = state.get("action", "finish")
        action_input = state.get("action_input", {})

        if action == "search_docs":
            query = action_input.get("query") or state["question"]
            hits_text = self._initial_search(query, state.get("department"))
            observation = hits_text or "No results found."
            state["context"] = f"{state.get('context', '')}\n{observation}".strip()
            observation = observation[:500]
        else:
            tool_executor = get_tool_executor(self.settings)
            observation = tool_executor.execute(action, action_input)

        trace = state.setdefault("trace", [])
        trace.append(AgentStep(
            step=state.get("step", 0) + 1,
            thought=state.get("thought", ""),
            action=action,
            action_input=action_input,
            observation=observation,
        ))
        state.setdefault("observations", []).append(str(observation))
        state["step"] = state.get("step", 0) + 1
        return state


class _LiteLLMAdapter:
    """Wraps LiteLLM for a simple invoke interface."""

    def __init__(self, settings: YourRAGSettings) -> None:
        self.settings = settings

    def invoke(self, prompt: str):
        import litellm
        # Use whatever model is configured
        model = self.settings.openai_model or "gpt-4o-mini"
        response = litellm.completion(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2)
        content = response.choices[0].message.content  # type: ignore
        return type("_Resp", (), {"content": content})()


# Singleton
react_agent_service = ReActAgentService()
