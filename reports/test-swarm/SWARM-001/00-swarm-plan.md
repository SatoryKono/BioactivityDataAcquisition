# Test Swarm Plan: SWARM-001

**Дата**: 2026-03-31 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 18431 |
| Passed | 18421 |
| Failed | 10 |
| Skipped | 118 |
| Error | 0 |
| Coverage (overall) | 87% |
| Coverage (domain) | 92% |
| Architecture tests | 48/58 pass |
| mypy errors | 0 |
| Median test time | 10ms |
| p95 test time | 50ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 80 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 35 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 85 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 30 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~106 | 95 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-app-unit ∥ L2-infra-unit-integ
3. L2-comp-iface-unit
