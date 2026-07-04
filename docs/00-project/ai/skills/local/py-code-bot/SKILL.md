> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/py-code-bot/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: py-code-bot description: Deprecated compatibility profile retained only to interpret historical py-code-bot references.

# py-code-bot

*Status: deprecated-compatibility*

## Objective

Historical compatibility entry retained only to interpret older references to `py-code-bot`.

## Source Of Truth

- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Current orchestration: `../../agents/ORCHESTRATION.md`
- Historical mirror context: `../../../docs/00-project/ai/skills/global/py-code-bot/SKILL.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Treat `py-code-bot` as a deprecated compatibility reference, not as the current production-code workflow.
1. Use `../../agents/ORCHESTRATION.md` for the active implementation path, where production code is written directly by the orchestrator.
1. Use this page only to interpret historical notes, mirrors, or workflow artifacts that still mention `py-code-bot`.
