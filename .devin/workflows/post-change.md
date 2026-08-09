---
auto_execution_mode: 0
description: Run BioETL post-change validation checklist after code edits (coordinated by master.md)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `.devin/workflows/master.md` (coordinator)

Follow `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

## Master Workflow Integration

This workflow is coordinated by `master.md` which provides:
- Conditional execution based on change scope
- Dependency management between workflows
- Error handling and rollback strategy
- Centralized reporting

## Steps

1. **Determine change scope** (coordinated by master.md):
   - Detect changed files: `src/**`, `tests/**`, `docs/**`, `configs/**`, `.devin/**`, `.codex/**`
   - Apply conditional execution matrix from master.md

2. Re-scan impacted code, configs, docs, and tests

3. If `src/bioetl/**/*.py` changed: refresh `reports/quality/module-coverage-inventory.json` (`source_tree_sha256` MUST change)

4. If AI guidance rules changed under `docs/00-project/ai/rules/cursor/`:
   ```bash
   uv run python -m scripts.ai.sync.cursor --deploy
   uv run python -m scripts.ai.sync.windsurf
   ```

5. Keep Devin workflows in `.devin/workflows/` aligned with Windsurf Cascade workflows when review/post-change/pre-commit/qodo-sync guidance changes

6. **Run shared validation** (from `shared-validation.md`):
   - Architecture validation
   - Code quality validation
   - Secrets validation
   - Technical debt validation

7. Run targeted checks:
   - `make lint`
   - `make test-architecture` (when architecture boundaries touched)
   - relevant unit/integration tests for changed modules

8. Assemble and verify the source-bound Proof-or-Stop bundle with
   `python -m scripts.engineering.qa proof-or-stop assemble|verify`. Treat
   `DEGRADED` and `STOP` as non-qualified lifecycle claims.

9. Report: checks run, checks skipped, mirror-sync status (Cursor / Windsurf / Devin workflows)

10. Confirm no silent breaking changes to CLI/API/schema contracts

11. **Report to master.md** with execution status and Proof-or-Stop outcome

## Conditional Execution

This workflow executes as MANDATORY for all change scopes per master.md matrix:
- `src/**`: ✅ Mandatory
- `tests/**`: ✅ Mandatory  
- `docs/**`: ✅ Mandatory
- `configs/**`: ✅ Mandatory
- `.devin/**`: ✅ Mandatory
- `.codex/**`: ✅ Mandatory

## Error Handling

- **BLOCKER failure**: Stop all workflows, report to master.md
- **Rollback**: Revert changes if possible
- **Reporting**: Provide clear error messages and actionable feedback

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
- Tracked `configs/**` YAML: placeholders / env refs only
- Always report execution status to master.md for coordination
