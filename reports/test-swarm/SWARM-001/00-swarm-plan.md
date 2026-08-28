# Test Swarm Plan: SWARM-001

**Дата**: 2026-02-26 12:00
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🔴 RED

## Baseline Snapshot
| Метрика | Значение |
|---------|----------|
| Total tests | 550 |
| Passed | 495 |
| Failed | 55 |
| Skipped | 0 |
| Error | 0 |
| Coverage (overall) | 81.2% |
| Coverage (domain) | 82.0% |
| Architecture tests | 58/58 pass |
| mypy errors | 0 |
| Median test time | 45ms |
| p95 test time | 200ms |

## Декомпозиция на L2-агентов

| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~192 | 45 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~133 | 42 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ | unit+integration | ~140 | 50 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ | unit | ~83 | 35 | P2 |
| 5 | L2-crosscutting | tests/architecture/ | arch+e2e+contract | ~106 | 38 | P2 |

## Порядок запуска
1. L2-domain-unit ∥ L2-crosscutting
2. L2-app-unit ∥ L2-infra-unit-integ
3. L2-comp-iface-unit
