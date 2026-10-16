______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-15'

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
- **Snapshot**: `global/` currently holds only its README — no curated non-local skill copies are committed (see Global Snapshot).
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
- `global/` — entrypoint README only; no skill snapshots currently committed
- `_references/` — reference bundles overlaid into local mirror
- `SKILLS-CATALOG.md` — consolidated skill registry
- `SKILLS-PRACTICAL-INDEX.md` — operational index with practical usage guidance and a recommended top-15 for BioETL

## Current Runtime Status (2026-07-10)

- The active project-local Codex skills under `.codex/skills/` are
  `agent-debugging`, `coderabbit-audit`, `new-pipeline`,
  `observability-dashboard`, `observability-prometheus`, `py-audit-bot`,
  `py-config-bot`, `py-debug-bot`, `py-doc-bot`, `py-plan-bot`, `py-test-bot`,
  `research-workflow`, `technical-designer-mermaid`, `vcr-record`, and
  `verify-architecture` (historical `documentation-cascade-audit`,
  `nci-analysis`, and `py-code-bot` names were removed).
- Evidence/decision helper skills are active when present in `.codex/skills/`
  and share common reference contracts instead of redefining the same workflow.
- Every active project skill is expected to provide `agents/openai.yaml`
  metadata and pass the Codex skill architecture gate.

## Global Snapshot

The [global snapshot directory](global/README.md) is a tracked documentation
entrypoint. No third-party snapshots or system-skill copies are currently
committed there. Machine-local global skills remain in their installed runtime
catalogue; CI does not import them. Repository-local skills continue to use the
canonical runtime sources and generated `local/` mirrors described above.
