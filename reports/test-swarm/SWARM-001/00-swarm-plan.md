# Test Swarm Plan: SWARM-001

**Дата**: 2025-06-07 10:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 26863 |
| Passed | 26813 |
| Failed | 50 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 88% |
| Coverage (domain) | 90% |
| Architecture tests | 124/162 pass |
| mypy errors | ~10k (native) |
| Median test time | 0.05s |
| p95 test time | 0.5s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~50 | 45 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~40 | 30 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~100 | 80 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~30 | 20 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~100 | 120 | P1 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-application-unit ∥ L2-infrastructure-unit-integ (параллельно)
3. L2-composition-interfaces-unit (после domain + app, т.к. composition зависит от них)
