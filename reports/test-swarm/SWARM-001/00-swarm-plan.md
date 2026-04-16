# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-16 10:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 9742 |
| Passed | 9742 |
| Failed | 0 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 86.5% |
| Coverage (domain) | 91.2% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 0.1s |
| p95 test time | 1.2s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~50 | 95 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~100 | 120 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~120 | 150 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~30 | 35 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~50 | 45 | P2 |

## Порядок запуска
1. L2-domain-unit || L2-crosscutting (параллельно — независимы)
2. L2-app-unit || L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
