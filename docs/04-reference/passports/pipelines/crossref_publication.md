# `crossref_publication`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:provider_entity]` | `pipeline:crossref_publication` |
| Status | `active` |
| Gold contract | `crossref.publication v1.0.0` |

## Назначение и обработка данных

Enrich publication records with CrossRef metadata via DOI resolution. Источник — `crossref:publication` на `https://api.crossref.org`; применяемые extraction/input filters: doi=IDs from data/input/dois.csv column doi; CLI may override the input CSV.
В business-проекцию входят .
Silver использует профиль `crossref.publication` и проверяет обязательные поля `doi`, `title`; невалидные записи направляются в `quarantine`.
Перед Gold применяется строгий Pandera-контракт `crossref.publication`; Gold filters/constraints заданы в entity config (6 групп правил).

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `http_api` · `crossref:publication` |
| Resource / tables | `publication` |
| Filters | `doi`: IDs from data/input/dois.csv column doi; CLI may override the input CSV |
| Selected fields | `system` (10 fields); `identifiers` (2 fields); `title` (1 fields); `authors` (7 fields); `journal` (2 fields); `issn` (4 fields); `year` (1 fields); `dates` (4 fields); `pagination` (4 fields); `citations` (5 fields); `subjects` (1 fields); `language` (1 fields); `publisher` (1 fields); `doc_type` (4 fields); `content_domain` (2 fields); `license` (1 fields) |

## Silver и Data Quality

- Normalization profile: `crossref.publication`.
- Partitioning: —.
- DQ thresholds: soft `0.05`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `crossref.publication v1.0.0`; strict validation: `True`.
- Write mode: `configured`.
- Technical exclusions: `_dq_*`, `_source_batch_id`, `_index`, `_lookup_method`, `_original_id`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run --pipeline crossref_publication` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run --pipeline crossref_publication --limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run --pipeline crossref_publication --run-type backfill --dry-run` | Проверяет backfill/rebuild path без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline crossref_publication --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline crossref_publication --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline crossref_publication` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Data Flow

```mermaid
flowchart LR
    Source["crossref:publication"]
    Filters["Effective request/input filters"]
    Bronze["Bronze append-only snapshot"]
    Silver["Silver profile: crossref.publication + DQ"]
    Quarantine["Quarantine / exclusion evidence"]
    Gold["Gold: crossref.publication (configured)"]
    Source --> Filters --> Bronze --> Silver
    Silver -->|valid| Gold
    Silver -->|invalid| Quarantine
```

## Evidence

- `effective_entity_config`: `configs/entities/crossref/publication.yaml`
- `pipeline_registration`: `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `run_cli`: `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/crossref/publication.yaml`
- `provider_config`: `configs/providers/crossref.yaml`
