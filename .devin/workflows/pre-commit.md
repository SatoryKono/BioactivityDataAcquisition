---
auto_execution_mode: 0
description: BioETL pre-commit validation (lint, architecture, coverage gate) (coordinated by master.md)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `.devin/workflows/master.md` (coordinator)

Run local quality gates before committing BioETL changes.

## Master Workflow Integration

This workflow is coordinated by `master.md` which provides:
- Conditional execution based on change scope
- Dependency management between workflows
- Error handling and rollback strategy
- Centralized reporting

## Conditional Execution

This workflow executes per master.md matrix:
- `src/**`: ⚪ Git hook only (when running as git hook)
- `tests/**`: ⚪ Git hook only (when running as git hook)
- `docs/**`: ❌ Skip
- `configs/**`: ❌ Skip
- `.devin/**`: ❌ Skip
- `.codex/**`: ❌ Skip

## Commands

```bash
make lint
make test-architecture
make test-cov-fast-stable
```

## Shared Validation

Use shared validation logic from `shared-validation.md`:
- Architecture validation
- Code quality validation
- Secrets validation
- Technical debt validation

## Fail Conditions

- `mypy --strict` or `ruff` errors in changed files
- Architecture boundary violations (import matrix, domain I/O, structlog in wrong layers)
- Coverage below project threshold on changed scope
- Unsanitized VCR cassettes or secret-like strings in diff
- Weakened test assertions without justification
- Technical-debt budget increases or widened exclusions

## On Failure

- Fix blockers first; do not relax quality budgets to pass
- Report which gate failed and the minimal fix path
- **BLOCKER failure**: Stop git commit, report to master.md
- **Rollback**: Block commit with clear error message

## Error Handling

- **BLOCKER failure**: Stop git commit, report to master.md
- **Reporting**: Provide clear error message and minimal fix path
- **Git hook integration**: Only runs when triggered as git hook
