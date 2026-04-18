# Test Swarm Plan: SWARM-001

**Дата**: 2026-04-17 09:29
**Mode**: full_audit
**Scope**: full project
**Overall Status**: 🟡 YELLOW

## Декомпозиция на L2-агентов
| # | L2 Agent ID | Scope | Тип тестирования | Est. files | workload_score | Приоритет |
|:-:|-------------|-------|-------------------|:----------:|:--------------:|:---------:|
| 1 | L2-domain-unit | tests/unit/domain/ | unit | ~50 | 95 | P1 |
| 2 | L2-app-unit | tests/unit/application/ | unit | ~30 | 35 | P1 |
| 3 | L2-infra-unit-integ | tests/unit/infrastructure/ | unit + integration | ~40 | 85 | P1 |
| 4 | L2-comp-iface-unit | tests/unit/composition/ | unit | ~15 | 20 | P2 |
| 5 | L2-crosscutting | tests/architecture/ | architecture | ~20 | 25 | P2 |
