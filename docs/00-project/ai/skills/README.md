______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-31'

______________________________________________________________________

# Skills Mirror in docs/

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-03-12 (Wave 6 consolidation)*

This directory stores published documentation for BioETL AI skills across supported runtimes.

## Surface Types

- **Canonical runtime source**: live skill behavior and trigger contracts are
  authored in runtime trees such as `.codex/skills/`.
- **Published mirror**: `docs/00-project/ai/skills/local/` and related indexes
  exist for discoverability and documentation stability.
- **Snapshot**: `global/` stores curated copies of selected non-local skills.
- **Reference mirror**: `_references/` stores read-only mirrored reference
  bundles used by skills consistency tooling.

## Non-Canonical Mirror Notice

`docs/00-project/ai/skills/**` is a published/internal mirror surface. It must
not define runtime behavior independently from tracked runtime skill trees such
as `.codex/skills/**`. Edit the active runtime skill first, then refresh this
mirror when behavior or contributor guidance changes.

## Canonical Source

- Canonical Codex runtime skill source: `.codex/skills/`
- No tracked Gemini skill tree exists on the current `main` checkout; treat
  Gemini skill references in docs as mirror or local-only guidance until a
  verified `.gemini/skills/**` tree is added.
- Legacy Claude mirrors under `ai/claude/` are being retired and must not be
  treated as the primary source for local skill behavior.
- `docs/00-project/ai/skills/local/` is a published mirror layer and may retain
  compatibility entries for navigation
- Edit runtime skill behavior in the runtime source first; do not treat
  `local/` as the primary authoring surface
- When active docs and mirrors diverge, prefer current runtime orchestration guidance from `.codex/agents/ORCHESTRATION.md`
- Cross-runtime ownership and sync rules are described in
  [AI Runtime Mirror Ownership](../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md).

## Layout

- `local/` — published mirror for repository-local skills
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
