# NebulaKB Application Experience Acceptance

This document records the application, feedback, dashboard, and workflow-node P1 acceptance surface.

Run:

```bash
bash scripts/quality-gate.sh application-experience-demo
```

The gate covers:

- Feedback reason categories, handwritten feedback, assignment, status, notes, and trend snapshots.
- Dashboard filters for time range, knowledge base, application, and user.
- Average retrieval latency, average generation latency, token usage, top questions, knowledge health trend, metric tooltips, empty states, anomaly highlights, chart export, and daily report export.
- Application template creation, copy, rollback, access statistics, embed config, and share-link permissions.
- Workflow node search, drag snap, loop boundary hint, node input/output preview, single-node debug, and the acceptance cases for knowledge-write, application, retrieval, tool, variable, loop, condition, document extract, reranker, and direct reply nodes.

The backing service is `ApplicationExperienceCompletion` in `apps/application/services/application_experience_completion.py`.
