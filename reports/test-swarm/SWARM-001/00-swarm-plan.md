# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-11
**Mode**: full_audit
**Scope**: весь проект
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 19890 |
| Passed | 19889 |
| Failed | 1 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 87% |
| Coverage (domain) | 92% |
| Architecture tests | 2454/2454 pass |
| mypy errors | 0 |
| Median test time | 0.01s |
| p95 test time | 0.05s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 85 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 92 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 78 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 35 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~106 | 110 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
