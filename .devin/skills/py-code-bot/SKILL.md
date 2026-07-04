---
name: py-code-bot
description: Deprecated compatibility profile retained only to interpret historical py-code-bot references.
---

# py-code-bot

*Status: deprecated-compatibility*

## Objective

Historical compatibility entry retained only to interpret older references to `py-code-bot`.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Current orchestration: `../../agents/ORCHESTRATION.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Historical mirror context: `../../../docs/00-project/ai/skills/global/py-code-bot/SKILL.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Treat `py-code-bot` as a deprecated compatibility reference, not as the current production-code workflow.
1. Use `MEMORY_USAGE.md` and `agent-memory.md` if you need to trace historical
   references back to current runtime guidance.
1. Use `../../agents/ORCHESTRATION.md` for the active implementation path, where production code is written directly by the orchestrator.
1. Use this page only to interpret historical notes, mirrors, or workflow artifacts that still mention `py-code-bot`.
