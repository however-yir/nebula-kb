# Contributing

Thanks for contributing to **LZKB**.

## Before you start

- Open an issue first for large changes.
- Keep PRs focused and small.
- Include reproducible steps and expected behavior for bug fixes.

## Development setup

1. Backend:

```bash
python -m uv pip install -r pyproject.toml
python apps/manage.py migrate
python main.py dev web
```

2. Frontend:

```bash
cd ui
npm install
npm run dev
```

## Pull request checklist

- [ ] The change is scoped and documented.
- [ ] Sensitive information is removed from logs/screenshots.
- [ ] New configuration keys are added to `.env.example` and `config_example.yml` when applicable.
- [ ] Backward compatibility is considered for existing deployments.

## Reporting bugs

Please use the issue templates and include:

- LZKB version
- Steps to reproduce
- Expected vs actual behavior
- Logs or screenshots (with sensitive data redacted)

## License note

By contributing, you agree your contribution is distributed under this repository's license.
