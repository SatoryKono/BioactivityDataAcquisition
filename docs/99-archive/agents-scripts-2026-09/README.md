# Archived Agent Scripts — Wave 7 Follow-up (2026-09-04)

Status: archived
Original location: `docs/00-project/ai/agents/scripts/` (4 py files + diagrams)
Archive location: `docs/99-archive/agents-scripts-2026-09/`

## Why archived

- Legacy generators outside canonical `scripts/ai/` and `scripts/engineering/` — not covered by `junie-mirror-contract.json` or `SKILLS-CATALOG.md`
- Referenced only from deprecated `docs/00-project/ai/agents/runtime/orchestration/py-team-orchestration.md` (8-agent adapted copy, now legacy alias)
- Canonical generators now in `scripts/ai/` and `scripts/engineering/` (e.g., `scripts/ai/junie/check_junie_mirror.sh`, `scripts/engineering/qa/`)

## Retired Python files

- `py-config-bot-1.py` and `py-config-bot-2.py` — replaced by `python -m scripts.schema ...` commands
- `py-team-orchestration.py` — replaced by `python -m scripts.engineering.qa check-terminology`
- `architecture-techdebt-automation.py` — replaced by maintained `scripts.engineering.qa` commands
- `diagrams/py-doc-bot-2.py` and `diagrams/py-doc-bot-3.py` — removed from the archive

These archived Python executables were removed on 2026-09-04. They must not be restored under `docs/99-archive/`.

## Retained files

- `diagrams/py-doc-bot-1.sh`
- `diagrams/py-doc-bot-4.sh`

## References updated

- `docs/00-project/ai/agents/runtime/orchestration/py-team-orchestration.md` now points to maintained module entrypoints.

## Related

- Issues: #10070 (RF-005), #10068 (Wave 7)
