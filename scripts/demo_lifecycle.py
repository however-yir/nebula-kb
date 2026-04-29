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

    print("\n1. Import, parse, chunk, and index documents")
    for filename in manifest["documents"]:
        content = (sample_dir / filename).read_text(encoding="utf-8")
        document = platform.ingest_document(kb.tenant_id, kb.id, filename, content)
        print(f"   OK {filename}: status={document.status}, chunks={len(document.chunks)}")

    broken_filename = manifest["broken_document"]
    broken = platform.ingest_document(
        kb.tenant_id,
        kb.id,
        broken_filename,
        (sample_dir / broken_filename).read_text(encoding="utf-8"),
    )
    print(f"   FAIL {broken_filename}: status={broken.status}, reason={broken.error}")

    print("\n2. Retrieval Q&A with citations and empty-result fallback")
    last_answer = None
    for item in manifest["questions"]:
        answer = platform.ask(kb.tenant_id, kb.id, item["text"])
        last_answer = answer
        print(f"   Q: {item['text']}")
        print(f"   A: {answer.answer}")
        print(f"   Citations: {', '.join(answer.citations) if answer.citations else 'none'}")
        if answer.fallback_reason:
            print(f"   Fallback: {answer.fallback_reason}")

    print("\n3. Human feedback and low-quality answer review")
    feedback_spec = manifest["feedback"]
    feedback = platform.submit_feedback(
        tenant_id=kb.tenant_id,
        question=feedback_spec["question"],
        answer=last_answer.answer if last_answer else "",
        rating=feedback_spec["rating"],
        reason=feedback_spec["reason"],
    )
    print(f"   Feedback {feedback.id}: rating={feedback.rating}, status={feedback.status}")
    print(f"   Low-quality answers: {len(platform.low_quality_answers(kb.tenant_id))}")
    platform.close_feedback(kb.tenant_id, feedback.id, owner="knowledge-ops")
    print(f"   Feedback {feedback.id} closed by {feedback.owner}")

    print("\n4. Operations metrics snapshot")
    metrics = platform.metrics(kb.tenant_id)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
