# `chembl_activity`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_activity` |
| Status | `active` |
| Gold contract | `chembl.activity v1.0.0` |

## Назначение и обработка данных

Extract biological activity records from ChEMBL API. Источник — `chembl.activity.curated` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: assay_type__in=B,F; data_validity_comment__isnull=true; pchembl_value__isnull=false; potential_duplicate=0; standard_flag=1; standard_relation==; standard_type__in=IC50,Ki; standard_units=nM; target_tax_id__isnull=false; activity_id=IDs from data/input/activity.csv column activity_id; CLI may override the input CSV.
В business-проекцию входят `activity_id`, `assay_id`, `molecule_id`, `target_id`, `publication_id`, `standard_relation`, `standard_value`, `standard_units` и ещё 59 полей.
Silver использует профиль `chembl.activity` и проверяет обязательные поля `activity_id`, `molecule_id`, `assay_id`, `target_id`, `publication_id`, `record_id`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.activity`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl.activity.curated` |
| Method / endpoint | `GET` · `https://www.ebi.ac.uk/chembl/api/data/activity` |
| Resource / tables | `activity` |
| Filters | `assay_type__in`: B,F; `data_validity_comment__isnull`: true; `pchembl_value__isnull`: false; `potential_duplicate`: 0; `standard_flag`: 1; `standard_relation`: =; `standard_type__in`: IC50,Ki; `standard_units`: nM; `target_tax_id__isnull`: false; `activity_id`: IDs from data/input/activity.csv column activity_id; CLI may override the input CSV |
| Selected fields | `system` (8 fields); `business` (67 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.activity`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.activity v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_activity` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_activity --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_activity --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_activity --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_activity --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_activity` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl.activity.curated"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.activity + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.activity (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/activity.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/activity.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
