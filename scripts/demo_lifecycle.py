#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from knowledge.services.asset_lifecycle_demo import KnowledgeAssetPlatform  # noqa: E402


def main() -> None:
    sample_dir = ROOT / "demo-data" / "knowledge-sample"
    manifest = json.loads((sample_dir / "manifest.json").read_text(encoding="utf-8"))

    platform = KnowledgeAssetPlatform()
    kb = platform.create_knowledge_base(
        tenant_id=manifest["tenant_id"],
        knowledge_base_id=manifest["knowledge_base"]["id"],
        name=manifest["knowledge_base"]["name"],
        owner=manifest["knowledge_base"]["owner"],
    )

    print("NebulaKB demo: knowledge asset lifecycle")
    print(f"Knowledge base: {kb.name} ({kb.id})")
    print(f"Initial health score: {platform.knowledge_base_health(kb.tenant_id, kb.id)['health_score']}")

    print("\n1. Import, parse, chunk, and index documents")
    for filename in manifest["documents"]:
        content = (sample_dir / filename).read_text(encoding="utf-8")
        document = platform.ingest_document(kb.tenant_id, kb.id, filename, content)
        print(f"   OK {filename}: status={document.status}, chunks={len(document.chunks)}")
        print(f"      Upload progress: {document.upload_progress}% format={document.file_format} source={document.source}")
        print(f"      Status path: {' -> '.join(document.status_history)}")
        for chunk in platform.chunk_preview(kb.tenant_id, document.id, limit=1):
            print(
                "      Chunk preview: "
                f"{chunk['citation']} | {chunk['source_locator']} | {chunk['excerpt']}"
            )

    broken_filename = manifest["broken_document"]
    broken = platform.ingest_document(
        kb.tenant_id,
        kb.id,
        broken_filename,
        (sample_dir / broken_filename).read_text(encoding="utf-8"),
    )
    print(f"   FAIL {broken_filename}: status={broken.status}, reason={broken.error}")
    print(f"      Failure summary: {broken.failure_summary}")
    print(f"      Status path: {' -> '.join(broken.status_history)}")

    print("\n2. Retrieval playground with keyword/vector scores and source locators")
    playground_question = manifest["questions"][0]["text"]
    print(f"   Playground selected knowledge base: {kb.id}")
    keyword_hits = platform.search(kb.tenant_id, kb.id, playground_question, mode="keyword")
    vector_hits = platform.search(kb.tenant_id, kb.id, playground_question, mode="vector")
    for hit in keyword_hits[:1]:
        print(f"   Keyword hit: {hit.citation} Score: {hit.score} Source locator: {hit.source_locator}")
    for hit in vector_hits[:1]:
        print(f"   Vector hit: {hit.citation} Score: {hit.score} Source locator: {hit.source_locator}")

    print("\n3. Retrieval Q&A with citations and empty-result fallback")
    answers_by_question = {}
    for item in manifest["questions"]:
        answer = platform.ask(kb.tenant_id, kb.id, item["text"])
        answers_by_question[item["text"]] = answer
        print(f"   Q: {item['text']}")
        print(f"   A: {answer.answer}")
        print(f"   Citations: {', '.join(answer.citations) if answer.citations else 'none'}")
        print(f"   Stream state: {answer.stream_state} events={', '.join(answer.stream_events)}")
        for hit in answer.hits[:2]:
            print(f"   Hit score: {hit.score} mode={hit.retrieval_mode} citation={hit.citation}")
        if answer.citations:
            locator = platform.locate_citation(kb.tenant_id, answer.citations[0])
            print(f"   Citation locator: {locator['source_locator']}")
        if answer.fallback_reason:
            print(f"   Fallback: {answer.fallback_reason}")

    print("\n4. Health metrics before feedback")
    before_feedback = platform.metrics(kb.tenant_id)
    print(json.dumps(before_feedback, ensure_ascii=False, indent=2))

    print("\n5. Negative feedback creates a governance task")
    feedback_spec = manifest["feedback"]
    rated_answer = answers_by_question.get(feedback_spec["question"])
    feedback = platform.submit_feedback(
        tenant_id=kb.tenant_id,
        knowledge_base_id=kb.id,
        question=feedback_spec["question"],
        answer=rated_answer.answer if rated_answer else "",
        citations=rated_answer.citations if rated_answer else [],
        rating=feedback_spec["rating"],
        reason=feedback_spec["reason"],
        owner=kb.owner,
    )
    print(f"   Feedback {feedback.id}: rating={feedback.rating}, status={feedback.status}")
    print(f"   Low-quality answers: {len(platform.low_quality_answers(kb.tenant_id, knowledge_base_id=kb.id))}")
    task = platform.list_governance_tasks(kb.tenant_id, knowledge_base_id=kb.id)[0]
    print(
        "   Governance task: "
        f"id={task.id}, owner={task.owner}, status={task.status}, "
        f"question={task.question}, citations={', '.join(task.citations) if task.citations else 'none'}"
    )

    print("\n6. Health metrics after feedback")
    after_feedback = platform.metrics(kb.tenant_id)
    print(json.dumps(after_feedback, ensure_ascii=False, indent=2))

    platform.close_feedback(kb.tenant_id, feedback.id, owner="knowledge-ops")
    print(f"   Feedback {feedback.id} closed by {feedback.owner}")

    print("\n7. Knowledge-base health dashboard")
    dashboard = platform.metrics_by_knowledge_base(kb.tenant_id)
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))

    print("\n8. Health metrics after governance closure")
    after_closure = platform.metrics(kb.tenant_id)
    print(json.dumps(after_closure, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
