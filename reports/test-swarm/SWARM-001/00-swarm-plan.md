# Test Swarm Plan: SWARM-001

**Дата**: 2026-05-28 09:30
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟢 GREEN

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 24553 |
| Passed | 24553 |
| Failed | 0 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 88% |
| Coverage (domain) | 95% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 120ms |
| p95 test time | 300ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~300 | 50 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~250 | 50 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~350 | 50 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~100 | 30 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~150 | 30 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-application-unit ∥ L2-infrastructure-unit-integ (параллельно)
3. L2-composition-interfaces-unit (после domain + app, т.к. composition зависит от них)
