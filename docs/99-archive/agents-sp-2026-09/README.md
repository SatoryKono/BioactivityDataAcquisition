# Archived sp-* Specialist Profiles — Wave 7 (2026-09-04)

Status: archived
Original location: `docs/00-project/ai/agents/agents/sp-*.md` (12 files)
Archive location: `docs/99-archive/agents-sp-2026-09/`

## Why archived

- Zero `subagent_type` / `spawn_agent` invocations across `.codex/` and `docs/` (rg 0 hits)
- All 12 failed `docs/00-project/ai/agents/policy/check_agent_consolidation.py --strict` with `missing frontmatter` (findings=12)
- >70% responsibility overlap with 6 minimal sufficient `py-*` runtime agents:
  - `sp-code-reviewer`, `sp-architect-reviewer` -> `py-audit-bot`
  - `sp-debugger` -> `py-debug-bot`
  - `sp-test-automator` -> `py-test-bot`
  - `sp-data-engineer`, `sp-database-optimizer`, `sp-api-designer`, etc. -> covered by `py-*` + skills
- Domain irrelevant or duplicate per `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` Wave 6 criteria, re-validated Wave 7

## Archived files (12)

- sp-api-designer.md
- sp-architect-reviewer.md
- sp-code-reviewer.md
- sp-data-engineer.md
- sp-database-optimizer.md
- sp-debugger.md
- sp-dependency-manager.md
- sp-git-workflow-manager.md
- sp-prompt-engineer.md
- sp-refactoring-specialist.md
- sp-scientific-literature-researcher.md
- sp-test-automator.md

## Minimal sufficient set after Wave 7

| Category | Count |
| --- | --- |
| BioETL core (py-*) | 6 (`py-audit-bot`, `py-plan-bot`, `py-debug-bot`, `py-test-bot`, `py-config-bot`, `py-doc-bot`) |
| Generic sp-* | 0 (archived) |
| Service (ORCHESTRATION.md, README.md) | 2 |
| Total in `docs/00-project/ai/agents/agents/` | 8 |

## References

- Matrix: `docs/00-project/ai/agents/policy/AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` Wave 7
- Mirror parity: `scripts/ai/junie/check_junie_mirror.sh --check` (still PASS)
- Checker: `docs/00-project/ai/agents/policy/check_agent_consolidation.py` now 0 files / 0 findings
- Issues: #10068 (RF-003), #10066 (RF-001 baseline)
