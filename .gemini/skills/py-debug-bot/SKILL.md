______________________________________________________________________

## name: py-debug-bot description: Execute BioETL py-debug-bot profile for role-specific workflow and constraints.

# py-debug-bot

## Objective

Run the role-specific workflow as defined in the py-debug-bot profile.

## Source Of Truth

- Primary profile: `../../agents/py-debug-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the current task.
1. Open and follow `../../agents/py-debug-bot.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After debugging, run `python -m memory.tooling.workflow post-task ...` and promote only durable fix patterns or incident knowledge.
