# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 9700 |
| Passed | 9626 |
| Failed | 74 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 82.0% |
| Coverage (domain) | 88.0% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 100ms |
| p95 test time | 500ms |

## Декомпозиция на L2-агентов
| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~200 | 150 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~150 | 140 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~150 | 120 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~80 | 30 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~100 | 30 | P2 |
