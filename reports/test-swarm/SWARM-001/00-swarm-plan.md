# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-22 09:55
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟢 GREEN

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 22144 |
| Passed | 22144 |
| Failed | 0 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 92% |
| Coverage (domain) | 95% |
| Architecture tests | Pass |
| mypy errors | 0 |
| Median test time | 0.1s |
| p95 test time | 0.4s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~200 | 80 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~150 | 35 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~150 | 35 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~50 | 20 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + ... | arch + e2e + ... | ~100 | 30 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
