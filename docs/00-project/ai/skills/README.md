# Skills Mirror in docs/

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-03-12 (Wave 6 consolidation)*

This directory stores documentation mirrors for Claude Code skills.

## Canonical Source

- Canonical local skill source: `.claude/skills/`
- Canonical local mirror: `docs/00-project/ai/skills/local/`
- Rule: edit skills only in `.claude/skills/`; never edit `docs/00-project/ai/skills/local/` manually.

## Layout

- `local/` — repo-local mirror from `.claude/skills/`
- `global/` — snapshot of selected global skills
- `_references/` — reference bundles overlaid into local mirror
- `SKILLS-CATALOG.md` — consolidated skill registry
- `SKILLS-PRACTICAL-INDEX.md` — operational index with practical usage guidance and a recommended top-15 for BioETL

## Wave 6 Consolidation (2026-03-12)

Removed 6 skills (Ledger framework + nci-analysis) and 2 OpenAI metadata files.
Runtime `.claude/skills/` now contains 6 active skills.
See `SKILLS-CATALOG.md` for full details.

## Global Snapshot

- `docs/00-project/ai/skills/global/` is a documentation snapshot of selected global skills.
- It is not the canonical source for repository-local skill behavior.

### System Skill References

- Internal system skills are mirrored under `docs/00-project/ai/skills/global/.system/`.
- These files are intentionally excluded from the published docs site.
