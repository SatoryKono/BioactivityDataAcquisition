# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-24T10:54:28Z
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 22124 |
| Passed | 22123 |
| Failed | 1 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 89% |
| Coverage (domain) | 90% |
| Architecture tests | 2593/2594 pass |
| mypy errors | 0 |
| Median test time | 15ms |
| p95 test time | 45ms |

## Декомпозиция на L2-агентов
| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 150 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~133 | 120 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 110 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 80 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~100 | 90 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-application-unit ∥ L2-infrastructure-unit-integ (параллельно)
3. L2-composition-interfaces-unit (после domain + app, т.к. composition зависит от них)
