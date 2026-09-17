# Debt heatmap — src/bioetl

| Зона | Сигнал | Нагрев |
|---|---|---|
| application/pipelines/pubmed | 14× nosec B405 (обоснованы, defusedxml) | тёплая (шум супрессий) |
| application/services/ops | концентрация type: ignore (hooks) | тёплая |
| application/core + pipelines facades | noqa F403 star-реэкспорты | умеренная |
| infrastructure/storage/silver | except Exception + NOSONAR (обоснованы) | низкая |
| domain (enums) | nosec B105 ложные срабатывания | низкая |

## Top-20
В scope доказанных единиц < 20; полный список — findings.json (8 записей: 3 NOT_PROVEN, 5 PROVEN P2/P3).

## Quick wins vs strategic
- Quick wins: TD-05, реестр супрессий, docstring-правки.
- Strategic: TD-02 (явные реэкспорты), TD-01 (типизация hooks/duck-type).
- Зависимостный: нет (defusedxml на месте).
