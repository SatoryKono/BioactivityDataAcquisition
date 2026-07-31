# `chembl_protein_class`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_protein_class` |
| Status | `active` |
| Gold contract | `chembl.protein_class v1.0.0` |

## Назначение и обработка данных

ChEMBL Protein Classification hierarchy (enzyme classes, receptor types, etc.). Источник — `chembl:protein_class` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: protein_class_id=IDs from data/input/protein_class.csv column protein_class_id; CLI may override the input CSV.
В business-проекцию входят `protein_class_id`, `parent_id`, `replaced_by`, `pref_name`, `short_name`, `protein_class_desc`, `definition`, `class_level` и ещё 2 полей.
Silver использует профиль `chembl.protein_class` и проверяет обязательные поля `class_level`, `pref_name`, `protein_class_id`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.protein_class`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl:protein_class` |
| Method / endpoint | `GET` · `https://www.ebi.ac.uk/chembl/api/data/protein_classification` |
| Resource / tables | `protein_classification` |
| Filters | `protein_class_id`: IDs from data/input/protein_class.csv column protein_class_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (10 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.protein_class`.
- Partitioning: `class_level`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.protein_class v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_protein_class` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_protein_class --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_protein_class --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_protein_class --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_protein_class --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_protein_class` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:protein_class"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.protein_class + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.protein_class (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/protein_class.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/protein_class.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
