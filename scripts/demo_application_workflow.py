#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from application.services.application_workflow_demo import (  # noqa: E402
    ApplicationWorkflowPlatform,
    WorkflowEdge,
    WorkflowNode,
)
from knowledge.services.asset_lifecycle_demo import KnowledgeAssetPlatform  # noqa: E402


def main() -> None:
    print("NebulaKB demo: feedback, dashboard, application workflow")

    knowledge = KnowledgeAssetPlatform()
    kb = knowledge.create_knowledge_base(
        tenant_id="tenant-demo",
        knowledge_base_id="kb-feedback",
        name="反馈治理样例库",
        owner="knowledge-ops",
    )
    document = knowledge.ingest_document(
        kb.tenant_id,
        kb.id,
        "feedback-loop.md",
        """
# 反馈治理

## 点赞点踩

点赞代表答案可接受，点踩代表低质答案，需要记录原因、引用和处理状态。

## 转治理任务

低质答案需要转为治理任务，由知识运营负责人补充或修复知识。
""",
    )
    answer = knowledge.ask(kb.tenant_id, kb.id, "点踩之后谁处理低质答案？")
    thumbs_up = knowledge.vote_answer(
        kb.tenant_id,
        kb.id,
        "点赞是否可用？",
        "点赞代表答案可接受。",
        vote="thumbs_up",
        citations=[document.chunks[0].citation],
    )
    thumbs_down = knowledge.vote_answer(
        kb.tenant_id,
        kb.id,
        answer.question,
        answer.answer,
        vote="thumbs_down",
        citations=answer.citations,
        reason="答案缺少处理状态和负责人。",
        owner="knowledge-ops",
    )
    task = knowledge.list_governance_tasks(kb.tenant_id, knowledge_base_id=kb.id)[0]
    dashboard = knowledge.operations_dashboard_first_screen(kb.tenant_id)

    print(f"Thumbs up feedback: rating={thumbs_up.rating}, status={thumbs_up.status}")
    print(f"Thumbs down feedback: rating={thumbs_down.rating}, status={thumbs_down.status}")
    print(f"Governance task: id={task.id}, owner={task.owner}, status={task.status}")
    print("Operations dashboard first screen:")
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))

    apps = ApplicationWorkflowPlatform()
    simple = apps.create_application("FAQ 助手", "simple", owner="app-ops")
    workflow = apps.create_application("反馈处理工作流", "workflow", owner="app-ops")
    apps.publish_version(workflow.id)
    api_key = apps.create_api_key(workflow.id, "demo")

    nodes = [
        WorkflowNode("start", "start", "Start"),
        WorkflowNode("condition", "condition", "低分判断"),
        WorkflowNode("answer", "answer", "返回处理结果"),
    ]
    edges = [
        WorkflowEdge("start", "condition"),
        WorkflowEdge("condition", "answer", "true"),
        WorkflowEdge("condition", "answer", "false"),
    ]
    validation_errors = apps.validate_connections(nodes, edges)
    condition_result = apps.test_condition(thumbs_down.rating, "equals", 1)
    run = apps.debug_workflow(workflow.id, nodes, edges, answer.question)

    print(f"Application created: simple id={simple.id}, type={simple.application_type}")
    print(f"Application created: workflow id={workflow.id}, type={workflow.application_type}")
    print(f"Published version: {workflow.version}, status={workflow.status}")
    print(f"API key: {api_key}")
    print("Workflow node docs:")
    print(json.dumps(apps.node_catalog(), ensure_ascii=False, indent=2))
    print(f"Connection validation: {'ok' if not validation_errors else validation_errors}")
    print(f"Condition test: {str(condition_result).lower()}")
    print(f"Workflow debug status: {run.status}")
    print("Run log events:")
    print(json.dumps([step["event"] for step in run.steps], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
