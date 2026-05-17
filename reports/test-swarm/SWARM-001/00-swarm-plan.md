# Test Swarm Plan: SWARM-001

**Дата**: 2024-05-17 12:00
**Mode**: full_audit
**Scope**: весь проект
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 3981 |
| Passed | 3971 |
| Failed | 10 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 86% |
| Coverage (domain) | 91% |
| Architecture tests | 120/120 pass |
| mypy errors | 0 |
| Median test time | 0.05s |
| p95 test time | 1.2s |

## Декомпозиция на L2-агентов
| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~37 | 7 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~65 | 13 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit | ~94 | 18 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~46 | 9 | P1 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | unit | ~107 | 21 | P1 |
