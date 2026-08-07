---
name: "py-debug-bot"
description: "Execute the read-only BioETL py-debug-bot profile for reproducing, isolating, and analyzing concrete failures. Use when tests, runtime behavior, CI logs, or user-provided stack traces need root-cause diagnosis."
---

# py-debug-bot

## Source Of Truth

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
runtime symptoms that require reproduction and root-cause guidance.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-debug-bot.md`.
1. Reproduce or explain why reproduction is blocked.
1. Isolate the smallest responsible code/config/test surface.
1. Return a bounded remediation proposal and focused regression commands to the
   authorized parent agent; do not modify files or runtime state.

## Expected Output

- Root cause.
- Remediation guidance and confidence.
- Reproduction command.
- Focused validation command and result.

## Validation

Run the failing test or closest focused equivalent. Broaden only when the fix
touches shared behavior.

## Fallback

If reproduction is impossible, preserve the stack trace or symptom, document the
missing precondition, and avoid speculative closure.
