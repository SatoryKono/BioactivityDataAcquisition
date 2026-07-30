# `chembl_tissue`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_tissue` |
| Status | `active` |
| Gold contract | `chembl.tissue v1.0.0` |

## Назначение и обработка данных

Extract tissues from ChEMBL API. Источник — `chembl:tissue` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: tissue_id=IDs from data/input/tissue.csv column tissue_chembl_id; CLI may override the input CSV.
В business-проекцию входят `pref_name`, `bto_id`, `bto_iri`, `bto_mapping_status`, `bto_ontology_version`, `caloha_id`, `efo_id`, `efo_iri` и ещё 6 полей.
Silver использует профиль `chembl.tissue` и проверяет обязательные поля `tissue_id`, `pref_name`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.tissue`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl:tissue` |
| Method / endpoint | `GET` · `https://www.ebi.ac.uk/chembl/api/data/tissue` |
| Resource / tables | `tissue` |
| Filters | `tissue_id`: IDs from data/input/tissue.csv column tissue_chembl_id; CLI may override the input CSV |
| Selected fields | `system` (6 fields); `identifiers` (1 fields); `business` (14 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.tissue`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.tissue v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_tissue` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_tissue --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_tissue --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_tissue --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_tissue --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_tissue` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:tissue"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.tissue + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.tissue (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/tissue.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/tissue.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
