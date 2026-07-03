---
auto_execution_mode: 0
description: BioETL pre-commit validation (lint, architecture, coverage gate)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Run local quality gates before committing BioETL changes.

## Commands

```bash
make lint
make test-architecture
make test-cov-fast-stable
```

## Fail Conditions

- `mypy --strict` or `ruff` errors in changed files
- Architecture boundary violations (import matrix, domain I/O, structlog in wrong layers)
- Coverage below project threshold on changed scope
- Unsanitized VCR cassettes or secret-like strings in diff

## On Failure

- Fix blockers first; do not relax quality budgets to pass
- Report which gate failed and the minimal fix path
