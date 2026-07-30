# `chembl_assay`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_assay` |
| Status | `active` |
| Gold contract | `chembl.assay v1.0.0` |

## Назначение и обработка данных

Extract bioassay definitions from ChEMBL API. Источник — `chembl.assay.curated` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: assay_type__in=B,F; confidence_score__gte=8; relationship_type=D; target_chembl_id__isnull=false; assay_id=IDs from data/input/assay.csv column assay_chembl_id; CLI may override the input CSV.
В business-проекцию входят `assay_id`, `assay_description`, `assay_type`, `assay_type_description`, `assay_test_type`, `assay_category`, `assay_group`, `assay_organism` и ещё 32 полей.
Silver использует профиль `chembl.assay` и проверяет обязательные поля `assay_id`, `assay_type`, `assay_description`, `target_id`, `publication_id`, `bao_format`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.assay`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl.assay.curated` |
| Resource / tables | `assay` |
| Filters | `assay_type__in`: B,F; `confidence_score__gte`: 8; `relationship_type`: D; `target_chembl_id__isnull`: false; `assay_id`: IDs from data/input/assay.csv column assay_chembl_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (40 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.assay`.
- Partitioning: `assay_type`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.assay v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_assay` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_assay --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_assay --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_assay --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_assay --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_assay` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl.assay.curated"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.assay + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.assay (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/assay.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/assay.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
