______________________________________________________________________

## name: py-architecture-debt-bot description: Execute the full BioETL architecture-debt reduction workflow: generate tasks from the exemptions registry, build an execution plan, coordinate targeted debt reduction, and close with verification across py-test-bot, py-config-bot, py-doc-bot, and py-audit-bot.

# py-architecture-debt-bot

## Objective

Run the role-specific workflow as defined in the py-architecture-debt-bot profile.

## Source Of Truth

- Primary profile: `../../../.claude/agents/py-architecture-debt-bot.md`
- Team orchestration: `../../../.claude/agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Deterministic helpers:
  - `python -m scripts.engineering.qa generate-debt-tasks`
  - `python -m scripts.engineering.qa reduce-architecture-debt`

## Workflow

1. Open and follow `../../../.claude/agents/py-architecture-debt-bot.md`.
1. Use the deterministic helpers before editing code or delegating subagents.
1. Keep `configs/` mutations delegated to `py-config-bot`.
1. Close every debt-reduction wave with `py-test-bot`, `py-doc-bot`, and `py-audit-bot`.
