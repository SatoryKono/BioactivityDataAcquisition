# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 9742 |
| Passed | 9735 |
| Failed | 5 |
| Skipped | 2 |
| Error | 0 |
| Coverage (overall) | 86.4% |
| Coverage (domain) | 91.2% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 0.04s |
| p95 test time | 1.2s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 85 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 45 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~140 | 120 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~83 | 35 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~106 | 38 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-app-unit ∥ L2-infra-unit-integ
3. L2-comp-iface-unit
