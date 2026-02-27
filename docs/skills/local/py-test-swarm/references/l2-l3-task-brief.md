# L2/L3 Task Brief Templates

## L2 Task Brief

```text
Task Brief: <agent-id>

Scope
- Layer/Module: <layer/module>
- Test paths: <test-paths>
- Source paths: <source-paths>
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
- reports/test-swarm/<task-id>/<agent-id>/report.md
- reports/test-swarm/<task-id>/<agent-id>/metrics.json
- reports/test-swarm/<task-id>/telemetry/raw/events-<agent-id>.jsonl

Escalation rule
- If workload-score >= 40, create L3 agents and aggregate their reports.
```

## L2 Prompt Template

Use this for delegated L2 tasks:

```text
Ты — L2 тестовый агент проекта BioETL. Твой scope: {scope-description}.

Контекст:
- BioETL: Hexagonal + Medallion + DDD
- Stack: Python 3.13, uv, pytest, pytest-asyncio, hypothesis, VCR.py, respx
- Thresholds: coverage >=85% overall, >=90% domain

Task Brief:
- test-paths: {test-paths}
- source-paths: {source-paths}
- test-type: {test-type}
- baseline-fail-count: {fail-count}
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
- report.md
- metrics.json
- telemetry/raw/events-{agent-id}.jsonl
```

## L3 Mandatory Prefix

Always prepend this to L3 prompt:

```text
ВАЖНО: Ты — листовой агент (L3). Ты НЕ можешь порождать дочерних агентов.
Выполняй всю работу самостоятельно. Даже при workload-score >= 40 не делегируй,
а отметь перегрузку в отчёте.
```

## Failure Classification Matrix

| Category | Signals | Typical action |
|----------|---------|----------------|
| Import/Module | ModuleNotFoundError, ImportError | validate package/init and boundaries |
| Type | TypeError, AttributeError | verify signatures/protocol contracts |
| Data/Validation | ValidationError, Pandera | inspect schema drift and fixtures |
| State | AssertionError | inspect side effects/order/state leakage |
| Infrastructure | Timeout/Connection errors | inspect VCR/mocks/retries |
| Contract | response shape changed | update contracts/cassettes |
| Flaky | intermittent pass/fail | rerun N times and classify |
| Env/Config | env-dependent behavior | normalize env/fixtures |
