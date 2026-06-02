#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from knowledge.services.asset_admin_completion import KnowledgeAssetAdminCompletion  # noqa: E402


def main() -> None:
    platform = KnowledgeAssetAdminCompletion()
    accounts = platform.initialize_demo_accounts()
    manifest = platform.demo_asset_manifest()
    kb = platform.import_demo_knowledge_base()
    copied = platform.copy_knowledge_base(kb.id, "Support Demo Copy")
    platform.archive_knowledge_base(copied.id)
    platform.update_tags(kb.id, add={"refund", "release"}, remove={"faq"})
    platform.update_owner(kb.id, "lead@nebulakb.local")
    platform.update_description(kb.id, "<p>Support policy knowledge base</p>")
    platform.set_visibility(kb.id, "private")
    platform.mark_version(kb.id, "baseline")
    platform.favorite(kb.id, "operator@nebulakb.local")
    platform.record_recent_visit(kb.id, "operator@nebulakb.local")
    binding = platform.model_binding_check(kb.id)
    embedding_change = platform.change_embedding_model(kb.id, "embedding-v2")
    platform.set_operational_note(kb.id, "Review quarterly.")

    document = platform._documents_for_kb(kb.id)[0]
    redirect = platform.redirect_after_upload(document.id)
    parse_log = platform.download_parse_log(document.id)
    chunk_ids = list(platform.chunk_quality_scores(document.id).keys())
    first_chunk = platform.edit_chunk(chunk_ids[0], "Refund requires citation evidence. Follow-up context matters")
    split_chunk = platform.split_chunk(first_chunk.id, "Follow-up")
    platform.batch_update_chunks([first_chunk.id, split_chunk.id], quality_score=92)
    platform.disable_chunk(split_chunk.id)

    resumed = platform.start_resumable_upload(kb.id, "refund-policy.md", 64, "local-upload")
    platform.append_upload_chunk(resumed.id, 64)
    platform.complete_upload(resumed.id, "Duplicate refund policy.")
    duplicate = resumed.duplicate_of
    platform.cancel_parse_task(resumed.id)

    hits = platform.search(
        "refund citation evidence",
        [kb.id],
        mode="hybrid",
        top_k=2,
        threshold=0.1,
        rerank=True,
    )
    answer = platform.ask_multi_knowledge(
        "refund citation evidence",
        [kb.id],
        context_enabled=True,
        answer_length="short",
    )
    exported = platform.export_retrieval_results(hits)
    package = platform.export_knowledge_base(kb.id)
    imported = platform.import_knowledge_base(package, "Imported Support Demo")
    deleted = platform.bulk_delete_knowledge_bases([imported.id])
    capacity_stats = platform.capacity_stats(kb.id)
    history = platform.change_history(kb.id)
    chunk_quality_scores = platform.chunk_quality_scores(document.id)
    cleaned = platform.clean_demo_data()

    print("NebulaKB demo: knowledge admin completion")
    print(f"Demo accounts: {', '.join(account['role'] for account in accounts)}")
    print(f"Demo data version: {manifest['version']}")
    print(f"Screenshot paths: {json.dumps(manifest['screenshots'], sort_keys=True)}")
    print(f"GIF source: {manifest['gif_source']}")
    print(f"Knowledge template: {kb.template_id}")
    print(f"Knowledge archived: {copied.status}")
    print(f"Knowledge copied: {copied.id}")
    print(f"Bulk delete: {deleted}")
    print(f"Tags: {sorted(kb.tags)}")
    print(f"Team and owner: {kb.team}, {kb.owner}")
    print(f"Capacity stats: {json.dumps(capacity_stats, sort_keys=True)}")
    print(f"Visibility: {kb.visibility}")
    print(f"Version and history: {kb.version}, {history}")
    print(f"Favorite users: {sorted(kb.favorites)}")
    print(f"Recent visits: {kb.recent_visits}")
    print(f"Model binding: {binding}")
    print(f"Embedding change warning: {embedding_change['status']}")
    print(f"Operational note: {kb.operational_note}")
    print(f"Document redirect: {redirect}")
    print(f"Duplicate document: {duplicate}")
    print(f"Parse stats: duration={document.parse_duration_ms}, chunks={document.chunk_count}")
    print(f"Vector/index status: {document.vector_status}/{document.index_status}")
    print(f"Parse log download: {parse_log.splitlines()[0]}")
    print(f"Cancelled parse: {resumed.cancelled}")
    print(f"Chunk edited version: {first_chunk.version}")
    print(f"Chunk split: {split_chunk.id}")
    print(f"Chunk disabled: {split_chunk.enabled}")
    print(f"Chunk quality scores: {chunk_quality_scores}")
    print(f"Hybrid retrieval hits: {len(hits)}")
    print(f"Rerank/top-k/threshold: enabled/2/0.1")
    print(f"Answer confidence: {answer['confidence']}")
    print(f"Context and length: {answer['context_enabled']}/{answer['answer_length']}")
    print(f"Retrieval export: {exported}")
    print(f"Demo cleanup count: {cleaned}")


if __name__ == "__main__":
    main()
