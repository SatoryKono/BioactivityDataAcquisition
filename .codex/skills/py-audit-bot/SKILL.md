______________________________________________________________________

## name: py-audit-bot description: Execute BioETL py-audit-bot profile for role-specific workflow and constraints.

# py-audit-bot

## Objective

Run the role-specific workflow as defined in the py-audit-bot profile.

## Source Of Truth

- Primary profile: `../../agents/py-audit-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the current task.
1. Open and follow `../../agents/py-audit-bot.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After the audit, run `python -m memory.tooling.workflow post-task ...` and promote only durable findings.
