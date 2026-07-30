# `chembl_compound_record`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_compound_record` |
| Status | `active` |
| Gold contract | `chembl.compound_record v1.0.0` |

## Назначение и обработка данных

Extract compound records from ChEMBL API. Источник — `chembl:compound_record` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: molecule_id=IDs from data/input/molecule.csv column molecule_chembl_id; CLI may override the input CSV.
В business-проекцию входят `record_id`, `molecule_id`, `publication_id`, `src_id`, `compound_key`, `compound_name`, `src_compound_id`.
Silver использует профиль `chembl.compound_record` и проверяет обязательные поля `molecule_id`, `publication_id`, `record_id`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.compound_record`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl:compound_record` |
| Method / endpoint | `GET` · `https://www.ebi.ac.uk/chembl/api/data/compound_record` |
| Resource / tables | `compound_record` |
| Filters | `molecule_id`: IDs from data/input/molecule.csv column molecule_chembl_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (7 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.compound_record`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.compound_record v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_compound_record` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_compound_record --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_compound_record --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_compound_record --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_compound_record --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_compound_record` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:compound_record"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.compound_record + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.compound_record (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/compound_record.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/compound_record.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
