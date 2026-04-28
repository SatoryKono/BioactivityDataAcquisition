# Test Swarm Plan: SWARM-001

**Дата**: $(date -u +"%Y-%m-%d %H:%M")
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 22727 |
| Passed | - |
| Failed | - |
| Skipped | - |
| Error | - |
| Coverage (overall) | - |
| Coverage (domain) | - |
| Architecture tests | - |
| mypy errors | - |
| Median test time | - |
| p95 test time | - |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~300 | 150 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~250 | 120 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~350 | 160 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~150 | 80 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~100 | 60 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
