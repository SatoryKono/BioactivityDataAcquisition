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
*Обновлено: 2026-07-10 (Codex skills refactor and metadata gates)*

This directory stores published documentation for BioETL AI skills across supported runtimes.

## Surface Types

- **Canonical runtime source**: live skill behavior and trigger contracts are
  authored in runtime trees such as `.codex/skills/`.
- **Published mirror**: `docs/00-project/ai/skills/local/` and related indexes
  exist for discoverability and documentation stability.
- **Snapshot**: `global/` may still hold curated copies of selected non-local skills (not the prompts library).
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

## Parity Contract

`scripts/ai/codex/skills-mirror-contract.json` is the reviewed contract for
Codex, Devin, and the transformed docs mirror. It requires equal Codex-Devin
`SKILL.md` entrypoint sets and complete catalog membership. Shared reference
files must match, while runtime-specific `SKILL.md` content, optional reference
presence, and `agents/openai.yaml` metadata are explicitly sanctioned variants.

Use `bash scripts/ai/codex/check_skills_mirror.sh --check` for the read-only CI
gate. Use `--sync` to regenerate only `local/`; it does not rewrite
`.devin/skills/**`.

## Layout

- `local/` — published mirror for repository-local skills
- `global/` — snapshot of selected global skills
- `_references/` — reference bundles overlaid into local mirror
- `SKILLS-CATALOG.md` — consolidated skill registry
- `SKILLS-PRACTICAL-INDEX.md` — operational index with practical usage guidance and a recommended top-15 for BioETL

## Current Runtime Status (2026-07-10)

- `documentation-cascade-audit` is now a project-local Codex skill under
  `.codex/skills/documentation-cascade-audit/`; matching user-global copies
  are not authoritative.
- Evidence/decision helper skills are active when present in `.codex/skills/`
  and share common reference contracts instead of redefining the same workflow.
- `nci-analysis` is an active concise project skill with reference material
  loaded by progressive disclosure.
- `py-code-bot` is retained only as a deprecated compatibility marker; active
  production changes are made by the orchestrator or the more specific `py-*`
  profile skill.
- Every active project skill is expected to provide `agents/openai.yaml`
  metadata and pass the Codex skill architecture gate.

## Global Snapshot

- `docs/00-project/ai/skills/global/` is a documentation snapshot of selected global skills.
- It is not the canonical source for repository-local skill behavior.
- **LICENSE thinning:** exact-duplicate Apache-2.0 license bodies are stored once
  under `global/_licenses/`; per-skill `LICENSE.txt` / `license.txt` files are
  short pointers. This does **not** break `local/` skill-mirrors generated from
  `.codex/skills` (`check_skills_mirror.sh` / `scripts/ai/sync/governance.py`).

### System Skill References

- Internal system skills are mirrored under `docs/00-project/ai/skills/global/.system/`.
- These files are intentionally excluded from the published docs site.
