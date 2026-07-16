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
   uv run python scripts/ai/sync_cursor_rules.py --deploy
   uv run python scripts/ai/sync_windsurf_rules.py
   ```
4. Keep Devin workflows in `.devin/workflows/` aligned with Windsurf Cascade workflows when review/post-change/pre-commit/qodo-sync guidance changes
5. Run targeted checks:
   - `make lint`
   - `make test-architecture` (when architecture boundaries touched)
   - relevant unit/integration tests for changed modules
6. Report: checks run, checks skipped, mirror-sync status (Cursor / Windsurf / Devin workflows)
7. Confirm no silent breaking changes to CLI/API/schema contracts

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
- Tracked `configs/**` YAML: placeholders / env refs only
