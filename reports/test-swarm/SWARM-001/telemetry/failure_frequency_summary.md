# Failure Frequency Summary

**Task ID**: SWARM-001
**Дата**: 2026-02-26 12:00

## Top 20 Flaky Tests
| Test ID | Total Runs | Pass Count | Fail Count | Failure Frequency | Flaky Index | Triage Status |
|---------|------------|------------|------------|-------------------|-------------|---------------|
| tests/architecture/test_compatibility_facade_inventory.py::test_inventory_doc_tables_match_yaml_registry | 5 | 4 | 1 | 20.0% | 0.20 | manual-review |

## Heatmap по слоям/модулям
- domain: 0 flaky
- application: 0 flaky
- infrastructure: 0 flaky
- composition: 0 flaky
- interfaces: 0 flaky
- crosscutting: 1 flaky

## Корреляция «длительность ↔ вероятность падения»
Анализ показывает слабую корреляцию (r=0.15) между длительностью теста и вероятностью падения.

## Разделение детерминированных vs flaky падений
- Детерминированные: 22
- Flaky: 5

## Динамика
Сравнение с baseline_report недоступно (первый прогон).
