---
name: py-test-bot
description: Execute BioETL py-test-bot profile for role-specific workflow and constraints. This skill serves as a convenient entry point for testing tasks.
---

# py-test-bot

## Objective

Run the role-specific workflow as defined in the py-test-bot profile. This skill provides a convenient entry point for testing tasks, while the actual agent logic resides in `.devin/agents/py-test-bot/AGENT.md`.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Primary profile: `../../agents/py-test-bot/AGENT.md`
- Team orchestration: `.codex/agents/ORCHESTRATION.md` (v4.3)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role-specific memory: matching `../../../docs/00-project/ai/memory/memory-py-*.md`
  sheet when one exists for this profile

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the current task.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and the matching role-specific
   memory sheet when it exists. If no role-specific sheet exists for this
   profile, record that and continue with project memory plus repo search.
1. Open and follow `../../agents/py-test-bot/AGENT.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After testing, run `python -m memory.tooling.workflow post-task ...` and promote only durable failure classifications or testing lessons.

## Skill vs Agent Usage

**When to use this skill:**
- Quick testing tasks with standard settings
- When you want a convenient entry point without navigating to agents
- For routine testing operations with default parameters

**When to use the agent directly:**
- Complex testing tasks requiring custom settings
- When you need fine-grained control over testing parameters
- For advanced testing scenarios beyond standard workflow

## Guidance

This skill is designed as a convenient shortcut for common testing scenarios. For complex or custom testing requirements, use the agent directly via `.devin/agents/py-test-bot/AGENT.md`.
