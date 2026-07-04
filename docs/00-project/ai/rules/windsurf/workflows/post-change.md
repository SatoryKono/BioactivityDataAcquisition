---
auto_execution_mode: 0
description: Run BioETL post-change validation checklist after code edits
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Follow `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

## Steps

1. Re-scan impacted code, configs, docs, and tests
2. If `src/bioetl/**/*.py` changed: refresh `reports/quality/module-coverage-inventory.json` (`source_tree_sha256` MUST change)
3. Run targeted checks:
   - `make lint`
   - `make test-architecture` (when architecture boundaries touched)
   - relevant unit/integration tests for changed modules
4. Report: checks run, checks skipped, mirror-sync status
5. Confirm no silent breaking changes to CLI/API/schema contracts

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
