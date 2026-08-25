## Parent

#9639. Слой `application/ports` законен по ADR-058; не возвращать его в `domain/ports`.

## Факт

Новые модули не проходят существующие architecture-контракты:

| Гейт | Нарушение |
|---|---|
| factories only in composition | `DQReportServiceFactory` (`application/ports/dq.py:33`), `WorkflowMetricsFactory` / `MetricsFactory` (`metrics.py:15,21`) |
| class naming suffixes | `ContractPolicyLoader`, `CompositeMergeStorage`, `StorageContextLike` |
| `from __future__ import annotations` | `application/ports/__init__.py`, `composition/contracts/__init__.py` |
| Port Protocol docstrings | `PaginationConfigLike`, `SourceConfigLike` в `domain/ports/source_config.py` |
| `@runtime_checkable` | `domain/ports/config_mapper.py` |
| domain-ports inventory | live `port_module_files` разошёлся с `RULES.md` / committed JSON |
| retirement triage | `config_mapper.py`, `pipeline_callbacks.py`, `source_config.py`, `entity_type.py` как untriaged zero-import |

## Цель

Поверхность ADR-058 совместима с действующими гейтами без роста бюджетов и без переноса factories в application.

## Правки

1. Factories — в `src/bioetl/composition/factories/` (или переименовать Protocol-like типы, если это не factories).
2. Naming: суффиксы по `test_naming_conventions.py` / consistency gate.
3. Добавить `from __future__ import annotations` там, где пакет не в sanctioned facade exception.
4. Docstrings + `@runtime_checkable` на Protocol-портах.
5. Regen `report-domain-ports-inventory` и triage zero-import с owner/evidence (бюджет 0 untriaged не поднимать).

## Definition of Done

- `test_di_compliance`, `test_naming_*`, `test_future_annotations_policy`, `test_documentation` (port docstrings), `test_strict_architecture_contracts` (runtime_checkable), ports inventory gate — зелёные.
- Zero-import untriaged count ≤ reviewed budget 0.
