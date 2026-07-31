# `chembl_publication_term`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_publication_term` |
| Status | `active` |
| Gold contract | `chembl.publication_term v1.0.0` |

## Назначение и обработка данных

Extract publication terms (MeSH, keywords) from ChEMBL Publication records. Источник — `chembl.publication_term.curated` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: doc_type=PUBLICATION; year__gte=1950; year__lte=2050; publication_id=IDs from data/input/publication.csv column publication_id; CLI may override the input CSV.
В business-проекцию входят `publication_id`, `term`, `term_type`, `mesh_id`, `qualifier`.
Silver использует профиль `chembl.publication_term` и проверяет обязательные поля `publication_id`, `term`, `term_type`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.publication_term`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `derived` · `chembl.publication_term.curated` |
| Method / endpoint | `GET` · `https://www.ebi.ac.uk/chembl/api/data/document` |
| Resource / tables | `document` |
| Filters | `doc_type`: PUBLICATION; `year__gte`: 1950; `year__lte`: 2050; `publication_id`: IDs from data/input/publication.csv column publication_id; CLI may override the input CSV |
| Selected fields | `system` (7 fields); `business` (5 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.publication_term`.
- Partitioning: `term_type`.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.publication_term v1.0.0`; strict validation: `True`.
- Write mode: `overwrite`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_publication_term` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_publication_term --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_publication_term --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_publication_term --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_publication_term --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_publication_term` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl.publication_term.curated"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.publication_term + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.publication_term (overwrite)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/publication_term.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/publication_term.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
