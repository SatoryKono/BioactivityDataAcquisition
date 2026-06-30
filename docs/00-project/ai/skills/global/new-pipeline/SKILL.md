> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Gemini: no tracked runtime counterpart on `main`; treat Gemini behavior as local-only or mirror guidance until a verified `.gemini/**` tree is added.
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: new-pipeline description: Scaffold a new BioETL provider/entity pipeline with configs, transformer registration, and baseline verification checks.

# New Pipeline

*Статус: internal-published (Internal / Extended)*

## Objective

Create a new ETL pipeline for a provider/entity pair in BioETL.

## Source Of Truth

- Codex SSOT: `.codex/skills/new-pipeline/SKILL.md`
- Claude runtime: runtime `new-pipeline` command entry

## Workflow

1. Open and follow the SSOT skill file for your active runtime.
1. If source examples are shell-specific, adapt commands to the current shell/environment.
1. Keep generated code/config aligned with project architecture rules in `AGENTS.md`.
1. Run verification commands from the source skill (or closest working equivalents in this environment).

## Notes

- The `.codex/skills/` directory is canonical for templates and detailed steps.
