---
name: py-audit-bot
description: Execute BioETL py-audit-bot profile for role-specific workflow and constraints. This skill serves as a convenient entry point for audit tasks.
---

# py-audit-bot

## Objective

Run the role-specific workflow as defined in the py-audit-bot profile. This skill provides a convenient entry point for audit tasks, while the actual agent logic resides in `.devin/agents/py-audit-bot/AGENT.md`.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Primary profile: `../../agents/py-audit-bot/AGENT.md`
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
1. Open and follow `../../agents/py-audit-bot/AGENT.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After the audit, run `python -m memory.tooling.workflow post-task ...` and promote only durable findings.

## Skill vs Agent Usage

**When to use this skill:**
- Quick audit tasks with standard configuration
- When you want a convenient entry point without navigating to agents
- For routine audit operations with default settings

**When to use the agent directly:**
- Complex audit tasks requiring custom configuration
- When you need fine-grained control over audit parameters
- For advanced audit scenarios beyond standard workflow

## Guidance

This skill is designed as a convenient shortcut for common audit scenarios. For complex or custom audit requirements, use the agent directly via `.devin/agents/py-audit-bot/AGENT.md`.
