# Test Swarm Plan: SWARM-001

**Дата**: 2026-05-15 10:46
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 23761 |
| Passed | 23736 |
| Failed | 25 |
| Skipped | 119 |
| Error | 0 |
| Coverage (overall) | 82% |
| Coverage (domain) | 88% |
| Architecture tests | fail |
| mypy errors | 5 |
| Median test time | 150ms |
| p95 test time | 500ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~226 | 50 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~283 | 60 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~389 | 80 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~167 | 45 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~339 | 70 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
