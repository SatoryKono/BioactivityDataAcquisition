# Test Swarm Plan: SWARM-001

**Дата**: 2026-05-19 11:06
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 24653 |
| Passed | 24622 |
| Failed | 31 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 90% |
| Coverage (domain) | 95% |
| Architecture tests | 58/58 pass |
| mypy errors | 485 |
| Median test time | 1s |
| p95 test time | 5s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~7609 | 90 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~5694 | 71 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~4821 | 63 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~1617 | 33 | P1 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~4925 | 69 | P1 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-application-unit ∥ L2-infrastructure-unit-integ (параллельно)
3. L2-composition-interfaces-unit (после domain + app, т.к. composition зависит от них)
