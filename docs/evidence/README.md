# NebulaKB Evidence Pack

This pack collects the shortest public proof path for reviewing the knowledge operations hub.

## Runtime Evidence

- Local lifecycle demo: `python scripts/demo_lifecycle.py`
- Test workflow: `.github/workflows/nebulakb-tests.yml`
- UI workflow: `.github/workflows/ui-ci.yml`
- Container workflows: `.github/workflows/build-and-push.yml`
- Release: `Health Baseline (2026-04-12)`

## Product And Architecture Evidence

- Demo GIF: `docs/assets/screenshots/demo.gif`
- Admin dashboard: `docs/assets/screenshots/admin-dashboard.svg`
- Knowledge base list: `docs/assets/screenshots/knowledge-base-list.svg`
- Document ingestion: `docs/assets/screenshots/document-ingestion.svg`
- QA feedback: `docs/assets/screenshots/qa-feedback.svg`
- Module boundaries: `docs/architecture/module-boundaries.md`
- Observability: `docs/observability.md`

## Verification Checklist

- Run migrations and start the local app.
- Create or seed a knowledge base.
- Ingest a document and confirm lifecycle state changes.
- Run a QA request and confirm feedback can be captured.
- Review the operations dashboard screenshots and observability notes.
- Open the latest GitHub Actions run and confirm the test/UI workflows are green.

