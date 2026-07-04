---
name: "py-debug-bot"
description: "Execute BioETL py-debug-bot profile for role-specific workflow and constraints."
---

# py-debug-bot

## Objective

Run the role-specific workflow as defined in the py-debug-bot profile.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Primary profile: `../../agents/py-debug-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role-specific memory: matching `../../../docs/00-project/ai/memory/memory-py-*.md`
  sheet when one exists for this profile

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the current task.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and the matching role-specific
   memory sheet when it exists. If no role-specific sheet exists for this
   profile, record that and continue with project memory plus repo search.
1. Open and follow `../../agents/py-debug-bot.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After debugging, run `python -m memory.tooling.workflow post-task ...` and promote only durable fix patterns or incident knowledge.
