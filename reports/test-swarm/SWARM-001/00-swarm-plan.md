# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-19T09:31:36Z
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 20909 |
| Passed | 20509 |
| Failed | 400 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 84.5% |
| Coverage (domain) | 89.2% |
| Architecture tests | 2532/2532 pass |
| mypy errors | 1204 |
| Median test time | 12ms |
| p95 test time | 450ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 55 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~133 | 35 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 60 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 25 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~104 | 30 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-application-unit ∥ L2-infrastructure-unit-integ
3. L2-composition-interfaces-unit
