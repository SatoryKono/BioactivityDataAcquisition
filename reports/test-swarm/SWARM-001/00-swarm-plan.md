# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 9742 |
| Passed | 9620 |
| Failed | 122 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 84% |
| Coverage (domain) | 89% |
| Architecture tests | 2400/2432 pass |
| mypy errors | 10 |
| Median test time | 150ms |
| p95 test time | 450ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 120 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~133 | 110 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ | unit + integration | ~140 | 115 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ | unit | ~83 | 60 | P2 |
| 5 | L2-crosscutting | tests/architecture/ | architecture + e2e + contract + bench | ~58 | 85 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-application-unit ∥ L2-infrastructure-unit-integ
3. L2-composition-interfaces-unit
