# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟢 GREEN

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 0 |
| Passed | 0 |
| Failed | 0 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 88% |
| Coverage (domain) | 92% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 0.2s |
| p95 test time | 1.0s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~100 | 50 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~100 | 60 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ | unit + integration | ~120 | 70 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ | unit | ~50 | 40 | P2 |
| 5 | L2-crosscutting | tests/architecture/ | architecture + e2e + contract + bench | ~100 | 80 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-application-unit ∥ L2-infrastructure-unit-integ
3. L2-composition-interfaces-unit
