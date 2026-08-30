# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 32592 |
| Passed | N/A |
| Failed | N/A |
| Skipped | N/A |
| Error | N/A |
| Coverage (overall) | N/A% |
| Coverage (domain) | N/A% |
| Architecture tests | N/A pass |
| mypy errors | N/A |
| Median test time | Ns |
| p95 test time | Ns |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~N | N | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~N | N | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~N | N | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~N | N | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~N | N | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
