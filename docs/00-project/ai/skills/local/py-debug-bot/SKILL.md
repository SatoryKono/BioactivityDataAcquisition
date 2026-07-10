> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-debug-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-debug-bot"
description: "Execute the BioETL py-debug-bot profile for reproducing, isolating, and fixing concrete failures. Use when tests, runtime behavior, CI logs, or user-provided stack traces need root-cause debugging."
---

# py-debug-bot

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
- Primary profile: `../../agents/py-debug-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role memory: `../../../docs/00-project/ai/memory/memory-py-debug-bot.md`

## Trigger Scope

Use this wrapper for failing tests, exceptions, timeouts, flaky behavior, or
runtime symptoms that require reproduction and a narrow fix.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-debug-bot.md`.
1. Reproduce or explain why reproduction is blocked.
1. Isolate the smallest responsible code/config/test surface.
1. Validate the fix with the focused failing test first, then adjacent checks.

## Expected Output

- Root cause.
- Fix summary.
- Reproduction command.
- Focused validation command and result.

## Validation

Run the failing test or closest focused equivalent. Broaden only when the fix
touches shared behavior.

## Fallback

If reproduction is impossible, preserve the stack trace or symptom, document the
missing precondition, and avoid speculative closure.
