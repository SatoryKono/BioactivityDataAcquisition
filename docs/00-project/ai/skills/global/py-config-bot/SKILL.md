> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Gemini: no tracked runtime counterpart on `main`; treat Gemini behavior as local-only or mirror guidance until a verified `.gemini/**` tree is added.
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: py-config-bot description: Execute BioETL py-config-bot profile for role-specific workflow and constraints.

# py-config-bot

*Статус: internal-published (Internal / Extended)*

## Objective

Run the role-specific workflow as defined in the py-config-bot profile.

## Source Of Truth

- Primary profile: `../../agents/py-config-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Open and follow `../../agents/py-config-bot.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
