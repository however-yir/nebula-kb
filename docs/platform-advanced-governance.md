# NebulaKB Platform Advanced Governance Acceptance

Run:

```bash
bash scripts/quality-gate.sh platform-advanced-demo
```

The gate covers:

- Reranker, voice, image, and fallback LLM tests.
- Model parameter presets, fallback chain configuration, and model cost statistics.
- Tool category, execution log, timeout, retry, and internal tool market description.
- Scheduled trigger, event trigger, trigger records, retry, parameter preview, and run statistics.
- User bulk import, user groups, role templates, login logs, and account anomaly hints.
- OIDC, SAML, LDAP, and CAS configuration tests, callback URL copy, SSO enable/disable, default login method, SSO error logs, and user mapping rules.
- Audit filtering/export.
- API rate limit policy, curl examples, frontend request example, and compatibility notes.

The backing service is `PlatformAdvancedCompletion` in `apps/system_manage/services/platform_advanced_completion.py`.
