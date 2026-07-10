> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-code-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-code-bot"
description: "Deprecated compatibility profile retained only to interpret historical py-code-bot references. Do not use for new implementation work; route current code changes through the active orchestrator and relevant py-* wrappers."
---

# py-code-bot

*Status: deprecated-compatibility*

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Current orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Historical mirror context: `../../../docs/00-project/ai/skills/global/py-code-bot/SKILL.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Retention Policy

Keep this skill only as a tombstone for historical notes, prompts, and mirrors
that still mention `py-code-bot`. Do not use it as an active implementation
workflow.

## Workflow

1. Treat `py-code-bot` as a deprecated compatibility reference, not as the current production-code workflow.
1. Use `MEMORY_USAGE.md` and `agent-memory.md` if you need to trace historical
   references back to current runtime guidance.
1. Use `../../agents/ORCHESTRATION.md` for the active implementation path, where production code is written directly by the orchestrator.
1. Use this page only to interpret historical notes, mirrors, or workflow artifacts that still mention `py-code-bot`.

## Expected Output

- Historical interpretation or routing guidance only.
- Explicit active replacement path.

## Validation

No implementation validation is attached to this tombstone. If work becomes
implementation, switch to the relevant active skill and validate there.
