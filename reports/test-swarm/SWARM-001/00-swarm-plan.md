# Test Swarm Plan: SWARM-001

**Дата**: 2026-08-19 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 31969 |
| Passed | 31792 |
| Failed | 1 |
| Skipped | 176 |
| Error | 0 |
| Coverage (overall) | 86% |
| Coverage (domain) | 91% |
| Architecture tests | 28/28 pass |
| mypy errors | 0 |
| Median test time | 0.05s |
| p95 test time | 1.2s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 35 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 25 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 30 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~54 | 15 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~50 | 10 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
