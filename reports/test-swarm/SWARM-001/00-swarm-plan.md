# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-02 09:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 19316 |
| Passed | 19312 |
| Failed | 4 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 86.6% |
| Coverage (domain) | 90.1% |
| Architecture tests | 240/240 pass |
| mypy errors | 0 |
| Median test time | 15s |
| p95 test time | 150s |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~5152 | 35 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~4465 | 30 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~4490 | 50 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~1843 | 20 | P2 |
| 5 | L2-crosscutting | crosscutting | architecture + e2e + contract + bench | ~3366 | 25 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting (параллельно — независимы)
2. L2-app-unit ∥ L2-infra-unit-integ (параллельно)
3. L2-comp-iface-unit (после domain + app, т.к. composition зависит от них)
