# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟢 GREEN

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 20922 |
| Passed | 20922 |
| Failed | 0 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 90.0% |
| Coverage (domain) | 95.0% |
| Architecture tests | Pass |
| mypy errors | 1257 |
| Median test time | 100ms |
| p95 test time | 200ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~50 | 100 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~50 | 100 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~50 | 100 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~20 | 30 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~50 | 30 | P2 |
