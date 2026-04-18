# Test Swarm Plan: SWARM-001

**Дата**: $(date -u +'%Y-%m-%d %H:%M')
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 20916 |
| Passed | - |
| Failed | - |
| Skipped | - |
| Error | - |
| Coverage (overall) | - |
| Coverage (domain) | - |
| Architecture tests | 2529 |
| mypy errors | - |
| Median test time | - |
| p95 test time | - |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~5360 | >90 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~4754 | >90 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~4706 | >90 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~1986 | >90 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~3626 | >90 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
