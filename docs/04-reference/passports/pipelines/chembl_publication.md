# `chembl_publication`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:chembl_publication` |
| Status | `active` |
| Gold contract | `chembl.publication v1.0.0` |

## Назначение и обработка данных

Extract scientific publications from ChEMBL API. Источник — `chembl.publication.curated` на `https://www.ebi.ac.uk/chembl/api/data`; применяемые extraction/input filters: doc_type=PUBLICATION; year__gte=1950; year__lte=2050.
В business-проекцию входят .
Silver использует профиль `chembl.publication` и проверяет обязательные поля `publication_id`, `publication_type`, `title`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `chembl.publication`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `chembl.publication.curated` |
| Resource / tables | `publication` |
| Filters | `doc_type`: PUBLICATION; `year__gte`: 1950; `year__lte`: 2050 |
| Selected fields | `system` (10 fields); `identifiers` (7 fields); `title` (1 fields); `abstract` (1 fields); `authors` (1 fields); `journal` (1 fields); `year` (1 fields); `pagination` (4 fields); `doc_type` (5 fields); `open_access` (2 fields); `provider_ids` (3 fields) |

## Silver и Data Quality

- Normalization profile: `chembl.publication`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `chembl.publication v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`, `_lookup_method`, `_original_id`, `pmc_id`, `publication_type_unified`, `publication_subclass`, `publication_class`, `oa_status`, `affiliation_list`, `author_orcids`, `is_oa`, `issn_list`, `language`, `publication_date`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline chembl_publication` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline chembl_publication --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline chembl_publication --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline chembl_publication --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline chembl_publication --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline chembl_publication` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["chembl.publication.curated"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: chembl.publication + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: chembl.publication (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/chembl/publication.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/publication.yaml`
- `provider_config`: `configs/providers/chembl.yaml`
