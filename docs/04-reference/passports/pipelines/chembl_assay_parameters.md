# `chembl_assay_parameters`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_assay_parameters` |
| Status | `active` |
| Gold contract | `chembl.assay_parameters v1.0.0` |

## Назначение и обработка данных

Extract experimental assay parameters from ChEMBL API. Источник — `chembl:assay_parameters` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: assay_param_id=IDs from data/input/assay_parameters.csv column assay_param_id; CLI may override the input CSV.
В business-проекцию входят `assay_param_id`, `assay_id`, `type_raw`, `parameter_type`, `parameter_relation`, `parameter_value`, `qudt_units`, `qudt_unit_iri` и ещё 14 полей.
Silver использует профиль `chembl.assay_parameters` и проверяет обязательные поля `assay_id`, `assay_param_id`, `parameter_type`, `type`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.assay_parameters`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `derived` · `chembl:assay_parameters` |
| Resource / tables | `assay_parameters` |
| Filters | `assay_param_id`: IDs from data/input/assay_parameters.csv column assay_param_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (22 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.assay_parameters`.
- Partitioning: `parameter_type`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.assay_parameters v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_assay_parameters` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_assay_parameters --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_assay_parameters --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_assay_parameters --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_assay_parameters --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_assay_parameters` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:assay_parameters"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.assay_parameters + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.assay_parameters (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/assay_parameters.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/assay_parameters.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
