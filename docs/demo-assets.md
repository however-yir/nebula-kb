# NebulaKB Demo Assets

This page keeps the local demo accounts, data import path, cleanup path, screenshot map, GIF source, and FAQ in one place.

## Demo Accounts

Run the knowledge-admin acceptance demo to inspect the generated demo accounts:

```bash
python scripts/demo_knowledge_admin.py
```

The seeded roles are:

| Email | Role |
| --- | --- |
| `admin@nebulakb.local` | `admin` |
| `operator@nebulakb.local` | `operator` |
| `viewer@nebulakb.local` | `viewer` |

## Demo Knowledge Import

The import path is backed by `demo-data/knowledge-sample/manifest.json` and is represented in code by `KnowledgeAssetAdminCompletion.import_demo_knowledge_base()`.

The demo data version for this acceptance batch is `2026.06`.

## Cleanup

Use `KnowledgeAssetAdminCompletion.clean_demo_data()` in scripts or tests when resetting local demo state. Local runtime files still live under `NEBULA_DATA_DIR`.

## Scenario Script

The supported demo flow is:

```text
import -> parse -> retrieve -> feedback -> governance
```

The script exercises template selection, archiving, copy, bulk delete, tags, owner/team metadata, capacity, visibility, versioning, favorites, recent visits, document resumable upload, duplicate detection, parse/reindex, chunk editing, hybrid search, rerank, top-k, threshold, confidence, context, answer length, and retrieval export.

## Screenshot Paths

| Screen | Asset |
| --- | --- |
| Knowledge base list | `docs/assets/screenshots/knowledge-base-list.svg` |
| Document ingestion | `docs/assets/screenshots/document-ingestion.svg` |
| QA feedback | `docs/assets/screenshots/qa-feedback.svg` |
| Admin dashboard | `docs/assets/screenshots/admin-dashboard.svg` |
| Knowledge health dashboard | `docs/assets/screenshots/knowledge-health-dashboard.svg` |

## GIF Source

The demo GIF is stored at `docs/assets/screenshots/demo.gif`. Regenerate it with `scripts/record_demo_gif.mjs` after UI path changes.

## FAQ

| Question | Answer |
| --- | --- |
| How do I import the demo knowledge base? | Run `python scripts/demo_knowledge_admin.py` or call `import_demo_knowledge_base()` from a test. |
| How do I clean local demo data? | Call `clean_demo_data()` and remove the local `NEBULA_DATA_DIR` only after stopping services. |
| Where are screenshots mapped? | Use the screenshot table above so README, docs, and release notes reference the same assets. |
| How do I verify the acceptance path? | Run `bash scripts/quality-gate.sh knowledge-admin-demo`. |
