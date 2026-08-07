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
3. If AI guidance rules changed under `docs/00-project/ai/rules/cursor/`:
   ```bash
   uv run python -m scripts.ai.sync.cursor --deploy
   uv run python -m scripts.ai.sync.windsurf
   ```
4. Run targeted checks:
   - `make lint`
   - `make test-architecture` (when architecture boundaries touched)
   - relevant unit/integration tests for changed modules
5. Report: checks run, checks skipped, mirror-sync status
6. Confirm no silent breaking changes to CLI/API/schema contracts

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
- Tracked `configs/**` YAML: secret-bearing values forbidden (use placeholders/env refs for tokens/passwords/connection strings); regular config modes and enum fields allowed
