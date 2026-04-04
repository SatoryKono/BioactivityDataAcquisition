______________________________________________________________________

## description: "Полный workflow устранения архитектурного долга BioETL. Режимы: full_cycle, generate_tasks, plan_reduction, execute_reduction."

# /architecture-debt

## Использование

```text
/architecture-debt [mode] [tasks_file]
```

**Режимы:** `full_cycle` (default), `generate_tasks`, `plan_reduction`, `execute_reduction`

## Инструкции

### Шаг 1: Parse arguments

- mode: first arg or `full_cycle`
- tasks_file: second arg or latest `tasks_architecture_metric_exemptions_*.json` from repo root

### Шаг 2: Run canonical deterministic helpers

```bash
python -m scripts.qa generate-debt-tasks
python -m scripts.qa reduce-architecture-debt
```

If `tasks_file` is explicitly provided, reuse it unless the user asks to regenerate tasks.

### Шаг 3: Launch the debt-reduction orchestrator

Use Agent tool with `subagent_type="py-architecture-debt-bot"`:

```text
Read `.claude/agents/py-architecture-debt-bot.md` and execute the full
architecture debt workflow.
mode: {mode}
tasks_file: {tasks_file or latest}
```

### Шаг 4: Output

1. Tasks file used
1. Execution plan used
1. Exemptions removed or narrowed
1. Hotspots reduced
1. Deferred items with reasons
