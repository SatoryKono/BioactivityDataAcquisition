# L2/L3 Task Brief Templates

## L2 Task Brief

```text
Task Brief: <agent_id>

Scope
- Layer/Module: <layer/module>
- Test paths: <test_paths>
- Source paths: <source_paths>
- Test type: unit | integration | e2e | architecture | contract
- Baseline FAIL count: <N>

Objectives
1. <goal 1>
2. <goal 2>

Constraints
- Keep import boundaries (RULES.md)
- No I/O in domain
- No secrets in code/logs/reports/VCR
- HTTP tests through VCR/respx
- Silver writes: Delta Lake only
- DI via constructors, no service locator

Change policy
- Allowed to change: <paths>
- Forbidden to change: <paths>

Timebox
- Workload size: Small | Medium | Large
- Runtime budget: <estimate>

Deliverables
- reports/test-swarm/<task_id>/<agent_id>/report.md
- reports/test-swarm/<task_id>/<agent_id>/metrics.json
- reports/test-swarm/<task_id>/telemetry/raw/events_<agent_id>.jsonl

Escalation rule
- If workload_score >= 40, create L3 agents and aggregate their reports.
```

## L2 Prompt Template

Use this for delegated L2 tasks:

```text
Ты — L2 тестовый агент проекта BioETL. Твой scope: {scope_description}.

Контекст:
- BioETL: Hexagonal + Medallion + DDD
- Stack: Python 3.13, uv, pytest, pytest-asyncio, hypothesis, VCR.py, respx
- Thresholds: coverage >=85% overall, >=90% domain

Task Brief:
- test_paths: {test_paths}
- source_paths: {source_paths}
- test_type: {test_type}
- baseline_fail_count: {fail_count}
- constraints: {constraints}
- timebox: {timebox}

Обязательный протокол:
- Phase 0: discovery + workload score
- Phase 1: stabilization (if mode includes failures)
- Phase 2: coverage expansion (if mode includes coverage)
- Phase 3: optimization (if mode includes optimize)
- Phase 4: telemetry/flakiness (if mode includes flakiness)
- Phase 5: reporting (always)

Создай:
- reports/test-swarm/<task_id>/<agent_id>/report.md
- reports/test-swarm/<task_id>/<agent_id>/metrics.json
- reports/test-swarm/<task_id>/telemetry/raw/events_<agent_id>.jsonl
```

## L3 Mandatory Prefix

Always prepend this to L3 prompt:

```text
ВАЖНО: Ты — листовой агент (L3). Ты НЕ можешь порождать дочерних агентов.
Выполняй всю работу самостоятельно. Даже при workload_score >= 40 не делегируй,
а отметь перегрузку в отчёте.
```

## Failure Classification Matrix

| Category        | Signals                          | Typical action                           |
| --------------- | -------------------------------- | ---------------------------------------- |
| Import/Module   | ModuleNotFoundError, ImportError | validate package/init and boundaries     |
| Type            | TypeError, AttributeError        | verify signatures/protocol contracts     |
| Data/Validation | ValidationError, Pandera         | inspect schema drift and fixtures        |
| State           | AssertionError                   | inspect side effects/order/state leakage |
| Infrastructure  | Timeout/Connection errors        | inspect VCR/mocks/retries                |
| Contract        | response shape changed           | update contracts/cassettes               |
| Flaky           | intermittent pass/fail           | rerun N times and classify               |
| Env/Config      | env-dependent behavior           | normalize env/fixtures                   |
