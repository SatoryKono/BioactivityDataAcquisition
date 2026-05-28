# План Test Swarm: SWARM-001

**Дата**: 2026-04-29 09:28
**Mode**: full_audit
**Scope**: full project
**Общий статус**: 🟢 GREEN

## Базовый снимок (Baseline)
| Метрика | Значение |
|---------|----------|
| Всего тестов | 18100 |

## Декомпозиция на L2-агентов
| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~N | 50 | P1 |
| 2 | L2-application-unit | tests/unit/application/ | unit | ~N | 50 | P1 |
| 3 | L2-infrastructure-unit-integ | tests/unit/infrastructure/ + tests/integration/ | unit + integration | ~N | 50 | P1 |
| 4 | L2-composition-interfaces-unit | tests/unit/composition/ + tests/unit/interfaces/ | unit | ~N | 30 | P2 |
| 5 | L2-crosscutting | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | architecture + e2e + contract + bench | ~N | 30 | P2 |
