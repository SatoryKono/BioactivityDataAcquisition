# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟢 GREEN

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 32183 |
| Passed | 32183 |
| Failed | 0 |
| Skipped | 176 |
| Error | 0 |
| Coverage (overall) | 88% |
| Coverage (domain) | 92% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 100s |
| p95 test time | 300s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 192 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 133 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 140 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 83 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~106 | 106 | P2 |

## Порядок запуска
1. L2-domain-unit \| L2-crosscutting (параллельно — независимы)
2. L2-app-unit \| L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
