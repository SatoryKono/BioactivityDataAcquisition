# `pubmed_publication`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:pubmed_publication` |
| Status | `active` |
| Gold contract | `pubmed.publication v1.0.0` |

## Назначение и обработка данных

Extract publication metadata from PubMed via Entrez API. Источник — `pubmed:publication` на `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`; применяемые extraction/input filters: pmid=IDs from data/input/pubmed.csv column pubmed_id; CLI may override the input CSV.
В business-проекцию входят .
Silver использует профиль `pubmed.publication` и проверяет обязательные поля `pmid`, `title`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `pubmed.publication`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `pubmed:publication` |
| Method / endpoint | `GET` · `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` |
| Resource / tables | `publication` |
| Filters | `pmid`: IDs from data/input/pubmed.csv column pubmed_id; CLI may override the input CSV |
| Selected fields | `system` (10 fields); `identifiers` (4 fields); `title` (1 fields); `abstract` (2 fields); `authors` (5 fields); `affiliations` (4 fields); `journal` (7 fields); `year` (1 fields); `dates` (6 fields); `pagination` (6 fields); `citations` (2 fields); `subjects` (5 fields); `funding` (1 fields); `chemicals` (1 fields); `doc_type` (4 fields); `language` (1 fields); `misc` (2 fields) |

## Silver и Data Quality

- Normalization profile: `pubmed.publication`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `pubmed.publication v1.0.0`; strict validation: `True`.
- Write mode: `scd2`.
- SCD2: current_flag_col=_is_current; valid_from_col=_valid_from; valid_to_col=_valid_to; version_col=_version.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`, `_lookup_method`, `_original_id`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline pubmed_publication` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline pubmed_publication --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline pubmed_publication --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline pubmed_publication --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline pubmed_publication --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline pubmed_publication` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["pubmed:publication"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: pubmed.publication + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: pubmed.publication (scd2)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/pubmed/publication.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/pubmed/publication.yaml`
- `provider_config`: `configs/providers/pubmed.yaml`
