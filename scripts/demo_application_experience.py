#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from application.services.application_experience_completion import ApplicationExperienceCompletion  # noqa: E402


def main() -> None:
    platform = ApplicationExperienceCompletion()

    first = platform.submit_feedback(
        "How do I validate citations?",
        1,
        "missing_citation",
        "The answer needs source evidence.",
    )
    platform.assign_feedback(first.id, "quality-owner")
    platform.update_feedback_status(first.id, "fixed", "Added missing citation.")
    second = platform.submit_feedback("Why is it slow?", 3, "slow_response", "Generation felt slow.")
    platform.update_feedback_status(second.id, "closed", "Tracked in latency review.")
    trend = platform.feedback_trend()
    dashboard = platform.operations_dashboard(
        time_range="30d",
        knowledge_base_id="kb-release",
        application_id="app-release",
        user_id="operator",
    )

    app = platform.create_from_template("review", "Feedback Review App", "app-owner")
    platform.publish_application(app.id)
    platform.publish_application(app.id)
    platform.rollback_application(app.id, 1)
    copied = platform.copy_application(app.id, "Feedback Review Copy")
    access_count = platform.record_application_access(app.id, count=12)
    embed = platform.configure_embed(app.id, ["support.example.com"], "light")
    share = platform.configure_share_link(app.id, "workspace", 7)

    catalog = platform.workflow_node_catalog()
    search = platform.search_nodes("retrieval")
    snapped = platform.snap_node_position(53, 71)
    loop_hint = platform.loop_boundary_hint(10)
    preview = platform.preview_node_io("retrieval")
    single_debug = platform.debug_single_node("retrieval", {"query": "refund"})
    node_summary = platform.node_acceptance_summary()
    chart = platform.export_dashboard_chart("low_quality_answer_rate")
    daily = platform.export_daily_report()

    print("NebulaKB demo: application experience completion")
    print(f"Feedback reason categories: {trend['by_reason']}")
    print(f"Handwritten feedback: {first.handwritten_feedback}")
    print(f"Feedback assignment/status/note: {first.owner}/{first.status}/{first.note}")
    print(f"Feedback trend: {json.dumps(trend, sort_keys=True)}")
    print(f"Dashboard filters: {json.dumps(dashboard['filters'], sort_keys=True)}")
    print(f"Average retrieval/generation latency: {dashboard['metrics']['average_retrieval_latency_ms']}/{dashboard['metrics']['average_generation_latency_ms']}")
    print(f"Token usage: {dashboard['metrics']['token_usage']}")
    print(f"Top questions: {dashboard['top_questions']}")
    print(f"Knowledge health trend: {dashboard['knowledge_health_trend']}")
    print(f"Metric tooltips: {sorted(dashboard['tooltips'].keys())}")
    print(f"Dashboard empty state: {dashboard['empty_state']}")
    print(f"Anomaly highlights: {dashboard['anomaly_highlights']}")
    print(f"Chart export: {chart}")
    print(f"Daily report export: {daily}")
    print(f"Application template: {app.template_id}")
    print(f"Application copy: {copied.id}")
    print(f"Application rollback version: {app.current_version}")
    print(f"Application access count: {access_count}")
    print(f"Embed config: {embed}")
    print(f"Share permissions: {share}")
    print(f"Node catalog count: {len(catalog)}")
    print(f"Node search: {search[0]['type']}")
    print(f"Node snap: {snapped}")
    print(f"Loop boundary hint: {loop_hint}")
    print(f"Node IO preview: {preview}")
    print(f"Single node debug: {single_debug['status']}")
    print(f"Node acceptance: {json.dumps(node_summary, sort_keys=True)}")


if __name__ == "__main__":
    main()
