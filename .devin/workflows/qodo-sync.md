---
auto_execution_mode: 0
description: Audit Cursor/Windsurf/Devin guidance against Qodo platform enforcement rules
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Compare tracked AI rules and Devin workflows with Qodo platform rules for `SatoryKono/BioactivityDataAcquisition`.

## Steps

1. Load Qodo rules via `/qodo-get-rules` skill, or use latest extract under `reports/quality/qodo-rules-extract-*.md` (current: `qodo-rules-extract-2026-07-16.md`, 66 IDs)
2. Read traceability index: `docs/00-project/ai/rules/cursor/07-qodo-enforcement.mdc`
3. Verify thematic rules in `docs/00-project/ai/rules/cursor/` cover all active Qodo rule themes (dedupe near-duplicates by intent)
4. Regenerate Cascade mirrors and confirm Devin workflows still match:
   ```bash
   uv run python scripts/ai/sync_cursor_rules.py --deploy
   uv run python scripts/ai/sync_windsurf_rules.py
   ```
5. Align `.devin/workflows/{review,post-change,pre-commit,qodo-sync,audit-documents}.md` with Windsurf Cascade workflow intent
6. If DeepWiki navigation notes are stale, update `.devin/wiki.json` pages `Project Governance and Rules` / `AI Runtime Governance` / `Secret Rules`
7. Report gaps: missing themes, stale index counts, Windsurf files over 12k chars, Devin workflow drift

## SSOT

- Rule content canonical source: `docs/00-project/ai/rules/cursor/*.mdc`
- Cursor deploy: `.cursor/rules/` via `scripts/ai/sync_cursor_rules.py --deploy`
- Windsurf/Cascade: `docs/00-project/ai/rules/windsurf/` via `scripts/ai/sync_windsurf_rules.py`
- Devin workflows: `.devin/workflows/` (tracked; keep parity with Cascade `review`, `post-change`, `pre-commit`, `qodo-sync`, plus specialized `audit-documents`)
- Devin DeepWiki: `.devin/wiki.json` (derived navigation; not normative)
