# Archived Agent Policy Docs — 2026-09-04

Status: archived
Original location: `docs/00-project/ai/agents/policy/` (4 files)
Archive location: `docs/99-archive/agents-policy-2026-09/`
Superseded by: `docs/00-project/ai/agents/policy/AGENT_GOVERNANCE.md`

## Why archived

- 4 docs-only files duplicated governance: `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` (Waves 1-7), `AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md`, `CONSOLIDATION_VALIDATION.md`, `SPECIALIST_PROFILE_TEMPLATE.md`
- All content merged into single `AGENT_GOVERNANCE.md` (naming + matrix + validation + templates)
- Old files had separate history but created link drift and maintenance overhead; single source reduces duplication >70%

## Archived files

- `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` — Waves 1-7 (now Section 2 in governance)
- `AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md` — namespaces + rename matrix (now Section 1)
- `CONSOLIDATION_VALIDATION.md` — checker commands (now Section 3)
- `SPECIALIST_PROFILE_TEMPLATE.md` — canonical/alias templates (now Section 4)

## References updated

- `docs/00-project/ai/agents/agents/README.md` Wave 7 reference updated to `AGENT_GOVERNANCE.md`
- Checker: `docs/00-project/ai/agents/policy/check_agent_consolidation.py` still at same path, now validates 0 files (all sp-* archived)

## Related

- Issues: #10069 (RF-004), #10068 (Wave 7)
