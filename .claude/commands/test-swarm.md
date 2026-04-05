______________________________________________________________________

## description: "Иерархическая система тестирования BioETL (L1→L2→L3). Режимы: full_audit, fix_failures, coverage_boost, optimize, flakiness_scan."

# /test-swarm

## Использование

```
/test-swarm [mode] [scope]
```

**Режимы:** `full_audit` (default), `fix_failures`, `coverage_boost`, `optimize`, `flakiness_scan`
**Scope:** `domain`, `application`, `infrastructure`, `composition`, `interfaces`, `{provider}`, or all.

## Инструкции

### Шаг 1: Parse arguments

- mode: first arg or `full_audit`
- scope: second arg or whole project
- `--flakiness-runs=N` (default 5), `--baseline-report=PATH`

### Шаг 2: Map scope → paths

| Scope            | Test paths                                                 | Source paths                 |
| ---------------- | ---------------------------------------------------------- | ---------------------------- |
| `domain`         | `tests/unit/domain/`                                       | `src/bioetl/domain/`         |
| `application`    | `tests/unit/application/`                                  | `src/bioetl/application/`    |
| `infrastructure` | `tests/unit/infrastructure/ tests/integration/`            | `src/bioetl/infrastructure/` |
| `{provider}`     | `tests/unit/*/{provider}/ tests/integration/*/{provider}/` | adapters + pipelines         |

### Шаг 3: Launch L1 orchestrator

Use Agent tool with `subagent_type="py-test-swarm"`:

```
Read `.claude/agents/py-test-swarm.md` and execute as L1 orchestrator.
task_id: SWARM-{NNN}, mode: {mode}, scope: {scope}
test_paths: {paths}, source_paths: {paths}
```

### Шаг 4: Output

1. Overall Status: GREEN/YELLOW/RED
1. Metrics table (before/after)
1. Agent list with statuses
1. Path to FINAL-REPORT.md

## Artifacts

```
reports/test-swarm/{task_id}/
├── 00-swarm-plan.md
├── L2-{scope}/report.md + metrics.json
├── telemetry/
└── FINAL-REPORT.md
```
