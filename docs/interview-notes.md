# Interview Notes

## One-Minute Pitch

NebulaKB is a knowledge operations hub that focuses on making knowledge assets continuously better: ingest documents, govern parsing and indexing, retrieve answers, capture feedback, review low-quality responses, and turn them into actionable knowledge work.

## What It Proves

- The project is positioned around knowledge lifecycle management, not only chat.
- Django, PostgreSQL, Redis, backend services, and UI surfaces support a full operational workflow.
- Demo assets show ingestion, governance, retrieval, feedback, and operations metrics.
- The boundary with `knowledgeops-agent` is explicit: NebulaKB is the operations/product layer, while KnowledgeOps Agent is the Spring AI backend baseline.
- Scripts and docs provide a repeatable lifecycle demo path.

## Best Technical Story

The strongest story is the feedback loop. A poor answer is not just a failed response; it becomes a knowledge operations event that can be reviewed, linked to assets, and used to improve retrieval quality over time.

## Tradeoffs To Explain

- The project is product-oriented, so some value is in workflow and operational framing rather than a single complex algorithm.
- Local startup depends on PostgreSQL and Redis; quick-install scripts exist to reduce first-run friction.
- Some model-provider behavior is intentionally abstracted because the knowledge lifecycle should not depend on one provider.

## Validation Path

```bash
cp .env.example .env
./scripts/bootstrap-local.sh --start
python apps/manage.py migrate
python main.py dev web
python scripts/demo_lifecycle.py
```

## Follow-Up Ideas

- Add a visible knowledge-quality dashboard screenshot with before/after metrics.
- Add a smoke test that proves ingestion -> retrieval -> feedback in one command.
- Add short resume bullets that distinguish NebulaKB from the Spring AI RAG backend project.
