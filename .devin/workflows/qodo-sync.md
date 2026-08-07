---
auto_execution_mode: 0
description: Audit Cursor/Windsurf/Devin guidance against Qodo platform enforcement rules (coordinated by master.md)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `.devin/workflows/master.md` (coordinator)

Compare tracked AI rules and Devin workflows with Qodo platform rules for `SatoryKono/BioactivityDataAcquisition`.

## Master Workflow Integration

This workflow is coordinated by `master.md` which provides:
- Conditional execution based on change scope
- Dependency management between workflows
- Error handling and rollback strategy
- Centralized reporting

## Conditional Execution

This workflow executes per master.md matrix:
- `src/**`: ❌ Skip
- `tests/**`: ❌ Skip
- `docs/**`: ❌ Skip
- `configs/**`: ⚪ If AI rules changed
- `.devin/**`: ❌ Skip
- `.codex/**`: ❌ Skip

## Steps

1. Load Qodo rules via `/qodo-get-rules` skill, or use latest extract under `reports/quality/qodo-rules-extract-*.md` (current: `qodo-rules-extract-2026-07-16.md`, 66 IDs)
2. Read traceability index: `docs/00-project/ai/rules/cursor/07-qodo-enforcement.mdc`
3. Verify thematic rules in `docs/00-project/ai/rules/cursor/` cover all active Qodo rule themes (dedupe near-duplicates by intent)
4. Regenerate Cascade mirrors and confirm Devin workflows still match:
   ```bash
   uv run python -m scripts.ai.sync.cursor --deploy
   uv run python -m scripts.ai.sync.windsurf
   ```
5. Align `.devin/workflows/{review,post-change,pre-commit,qodo-sync,audit-documents}.md` with Windsurf Cascade workflow intent
6. If DeepWiki navigation notes are stale, update `.devin/wiki.json` pages `Project Governance and Rules` / `AI Runtime Governance` / `Secret Rules`
7. Report gaps: missing themes, stale index counts, Windsurf files over 12k chars, Devin workflow drift

## SSOT

- Rule content canonical source: `docs/00-project/ai/rules/cursor/*.mdc`
- Cursor deploy: `.cursor/rules/` via `scripts/ai/sync/cursor.py --deploy`
- Windsurf/Cascade: `docs/00-project/ai/rules/windsurf/` via `scripts/ai/sync/windsurf.py`
- Devin workflows: `.devin/workflows/` (tracked; keep parity with Cascade `review`, `post-change`, `pre-commit`, `qodo-sync`, plus specialized `audit-documents`)
- Devin DeepWiki: `.devin/wiki.json` (derived navigation; not normative)

## Error Handling

- **WARNING failure**: Log but continue, report to master.md
- **Reporting**: Report gaps and drifts
- **Non-blocking**: Qodo sync failures don't stop other workflows
