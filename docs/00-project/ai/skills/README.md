# Skills Mirror in docs/

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-03-12 (Wave 6 consolidation)*

This directory stores published documentation for BioETL AI skills across supported runtimes.

## Canonical Source

- Canonical Codex runtime skill source: `.codex/skills/`
- `docs/00-project/ai/skills/local/` is a published mirror layer and may retain compatibility entries for navigation
- Edit runtime skill behavior in the runtime source first; do not treat `local/` as the primary authoring surface
- When active docs and mirrors diverge, prefer current runtime orchestration guidance from `.codex/agents/ORCHESTRATION.md`

## Layout

- `local/` — repo-local mirror from `.claude/skills/`
- `global/` — snapshot of selected global skills
- `_references/` — reference bundles overlaid into local mirror
- `SKILLS-CATALOG.md` — consolidated skill registry
- `SKILLS-PRACTICAL-INDEX.md` — operational index with practical usage guidance and a recommended top-15 for BioETL

## Wave 6 Consolidation (2026-03-12)

Removed 6 skills (Ledger framework + nci-analysis) and 2 OpenAI metadata files.
Current active orchestration no longer uses `py-code-bot` as a first-line production-code step; production code is written directly by the orchestrator.
See `SKILLS-CATALOG.md` for full details.

## Global Snapshot

- `docs/00-project/ai/skills/global/` is a documentation snapshot of selected global skills.
- It is not the canonical source for repository-local skill behavior.

### System Skill References

- Internal system skills are mirrored under `docs/00-project/ai/skills/global/.system/`.
- These files are intentionally excluded from the published docs site.
