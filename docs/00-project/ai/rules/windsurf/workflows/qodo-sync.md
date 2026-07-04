---
auto_execution_mode: 0
description: Audit Cursor/Windsurf rules against Qodo platform enforcement rules
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Compare tracked AI rules with Qodo platform rules for `SatoryKono/BioactivityDataAcquisition`.

## Steps

1. Load Qodo rules via `/qodo-get-rules` skill (or `POST /rules/search`)
2. Read traceability index: `docs/00-project/ai/rules/cursor/07-qodo-enforcement.mdc`
3. Verify thematic rules in `docs/00-project/ai/rules/cursor/` cover all active Qodo rules
4. Regenerate Windsurf mirror:
   ```bash
   uv run python scripts/ai/sync_windsurf_rules.py
   ```
5. Report gaps: missing rules, stale index counts, files over 12k chars

## SSOT

- Rule content canonical source: `docs/00-project/ai/rules/cursor/*.mdc`
- Windsurf deploy: derived via `scripts/ai/sync_windsurf_rules.py`
