# `chembl_target_protein_classification`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_target_protein_classification` |
| Status | `active` |
| Gold contract | `chembl.target_protein_classification v2.2.0` |

## Назначение и обработка данных

Derived ChEMBL target-to-protein-classification relation rows. Источник — `chembl:target_protein_classification` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: target_id=IDs from data/input/target_protein_classification.csv column target_id; CLI may override the input CSV.
В business-проекцию входят `target_id`, `component_id`, `leaf_id`, `path_ids`, `path_names`, `path_labels`, `depth`, `root_id` и ещё 32 полей.
Silver использует профиль `chembl.target_protein_classification` и проверяет обязательные поля `target_id`, `classification_status`, `dataset_version`, `source_snapshot_fingerprint`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.target_protein_classification`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `derived` · `chembl:target_protein_classification` |
| Resource / tables | `target_protein_classification` |
| Filters | `target_id`: IDs from data/input/target_protein_classification.csv column target_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (40 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.target_protein_classification`.
- Partitioning: `classification_status`.
- DQ thresholds: soft `0.01`, hard `0.05`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.target_protein_classification v2.2.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_target_protein_classification` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_target_protein_classification --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_target_protein_classification --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_target_protein_classification --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_target_protein_classification --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_target_protein_classification` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:target_protein_classification"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.target_protein_classification + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.target_protein_classification (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/target_protein_classification.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/target_protein_classification.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
