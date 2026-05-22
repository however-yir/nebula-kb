#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from knowledge.services.asset_lifecycle_demo import KnowledgeAssetPlatform  # noqa: E402


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            tokens.append(token)
            tokens.extend(token[index : index + 2] for index in range(len(token) - 1))
        elif len(token) > 1:
            tokens.append(token)
    return [token for token in tokens if len(token) > 1]


def cluster_questions(questions: Iterable[str]) -> list[dict[str, object]]:
    clusters: list[dict[str, object]] = []
    for question in questions:
        terms = set(tokenize(question))
        matched_cluster = None
        for cluster in clusters:
            cluster_terms = cluster["terms"]
            if terms & cluster_terms:
                matched_cluster = cluster
                break
        if matched_cluster is None:
            clusters.append({"terms": set(terms), "questions": [question]})
        else:
            matched_cluster["terms"].update(terms)
            matched_cluster["questions"].append(question)

    output: list[dict[str, object]] = []
    for index, cluster in enumerate(clusters, start=1):
        keywords = sorted(cluster["terms"])[:6]
        output.append(
            {
                "cluster_id": f"miss-{index}",
                "size": len(cluster["questions"]),
                "keywords": keywords,
                "questions": cluster["questions"],
            }
        )
    return output


def load_questions(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(raw)
        if isinstance(payload, list):
            return [str(item) for item in payload]
        if isinstance(payload, dict):
            questions = payload.get("questions", [])
            return [str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in questions]
    return [line.strip() for line in raw.splitlines() if line.strip()]


def demo_unanswered_questions() -> list[str]:
    sample_dir = ROOT / "demo-data" / "knowledge-sample"
    manifest = json.loads((sample_dir / "manifest.json").read_text(encoding="utf-8"))
    platform = KnowledgeAssetPlatform()
    kb = platform.create_knowledge_base(
        tenant_id=manifest["tenant_id"],
        knowledge_base_id=manifest["knowledge_base"]["id"],
        name=manifest["knowledge_base"]["name"],
        owner=manifest["knowledge_base"]["owner"],
    )
    for filename in manifest["documents"]:
        platform.ingest_document(
            kb.tenant_id,
            kb.id,
            filename,
            (sample_dir / filename).read_text(encoding="utf-8"),
        )
    for item in manifest["questions"]:
        platform.ask(kb.tenant_id, kb.id, item["text"])
    return platform.metrics(kb.tenant_id)["unanswered_questions"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster unanswered NebulaKB questions by shared keywords.")
    parser.add_argument("--input", type=Path, help="Text or JSON file containing unanswered questions.")
    args = parser.parse_args()

    questions = load_questions(args.input) if args.input else demo_unanswered_questions()
    print(json.dumps(cluster_questions(questions), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
