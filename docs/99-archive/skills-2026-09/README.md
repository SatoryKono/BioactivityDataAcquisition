# Archived Skills — 2026-09-04

Status: archived
Original location: `docs/00-project/ai/skills/local/deep-research`, `documentation-audit` + `_references/local/deep-research`, `documentation-audit`
Archive location: `docs/99-archive/skills-2026-09/`

## Why archived

- Incomplete skills in `local/` without `SKILL.md` (only `references/`), not in `.codex/skills/` SSOT and not in `SKILLS-CATALOG.md` (14)
- Zero `agents/openai.yaml` invocations, not covered by `skills-mirror-contract.json` canonical set
- `_references` mirrors for those skills also archived (reference bundles without canonical skill)

## Archived

- `deep-research/` (references: critique-framework, report-templates, search-patterns, source-evaluation)
- `documentation-audit/` (references: audit-checklist, report-template)
- `_references-deep-research/` and `_references-documentation-audit/` (mirrored bundles)

## Minimal sufficient set after

- `.codex/skills/` 14 + `docs/00-project/ai/skills/local/` 14 (1:1) — `check_skills_mirror.sh --check PASS`
- `global/` and `_references/local/technical-designer-mermaid` retained per contract

## Related

- Issues: RF-003 (skills)
