# `chembl_cell_line`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_cell_line` |
| Status | `active` |
| Gold contract | `chembl.cell_line v1.0.0` |

## Назначение и обработка данных

Extract cell lines from ChEMBL API. Источник — `chembl:cell_line` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: cell_chembl_id=IDs from data/input/cell.csv column cell_chembl_id; CLI may override the input CSV.
В business-проекцию входят `cell_id`, `cell_name`, `cell_description`, `cell_source_tissue`, `cell_source_organism`, `cell_source_taxonomy_id`, `cell_type`, `cellosaurus_id` и ещё 9 полей.
Silver использует профиль `chembl.cell_line` и проверяет обязательные поля `cell_id`, `cell_name`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.cell_line`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl:cell_line` |
| Resource / tables | `cell_line` |
| Filters | `cell_chembl_id`: IDs from data/input/cell.csv column cell_chembl_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (17 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.cell_line`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.cell_line v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_cell_line` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_cell_line --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_cell_line --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_cell_line --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_cell_line --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_cell_line` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl:cell_line"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.cell_line + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.cell_line (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/cell_line.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/cell_line.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
