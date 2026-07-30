# `composite_publication`

> Generated documentation projection. Do not edit manually.

## Обзор

| Параметр | Значение |
| --- | --- |
| Typed identity `[type:composite]` | `composite:composite_publication` |
| Status | `active` |
| Gold contract | `composite.publication v1.0.0` |

## Назначение и обработка данных

Composite pipeline `composite_publication` использует seed `chembl_publication` и объединяет его с configured dependencies/enrichers.
Join keys, cardinality и source tables берутся из composite configuration; merge и conflict resolution выполняются общей CompositePipelineRunner.
После merge применяется configured cross-validation; исключённые значения направляются в quarantine или nullification branch согласно composite policy.
Результат проходит строгий Gold-контракт `composite.publication` и публикует manifest/checkpoint evidence.

## Извлечение данных

| Аспект | Значение |
| --- | --- |
| Source | `composite` · `chembl_publication` |
| Resource / tables | `silver/chembl/publication`, `silver/crossref/publication`, `silver/openalex/publication`, `silver/pubmed/publication`, `silver/semanticscholar/publication` |
| Filters | `crossref_publication`: doi IS NOT NULL; `openalex_publication`: doi IS NOT NULL OR pmid IS NOT NULL; `pubmed_publication`: pmid IS NOT NULL; `semanticscholar_publication`: doi IS NOT NULL OR title IS NOT NULL |

## Silver и Data Quality

- Normalization profile: `composite.publication`.
- Partitioning: —.
- DQ thresholds: soft `0.1`, hard `0.5`; invalid policy `quarantine`.

## Gold

- Contract: `composite.publication v1.0.0`; strict validation: `True`.
- Write mode: `configured`.

## Операторские команды

| Задача | Команда | Результат |
| --- | --- | --- |
| Запуск | `bioetl run-composite --composite publication` | Запускает pipeline с effective config. |
| Ограниченный запуск | `bioetl run-composite --composite publication --seed-limit 100` | Ограничивает число обрабатываемых записей. |
| Безопасная проверка | `bioetl run-composite --composite publication --use-cached-bronze --dry-run` | Проверяет cached Bronze composite без записи. |
| Quarantine | `bioetl quarantine inspect --pipeline composite_publication --limit 100` | Показывает quarantined и Silver-filter records; доступны --error-code и --run-id. |
| Статистика исключений | `bioetl quarantine stats --pipeline composite_publication --group-by reason-code` | Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует. |
| Checkpoint | `bioetl checkpoint inspect --pipeline composite_publication` | Показывает checkpoint и связанные audit/manifest anchors. |
| Manifest | `bioetl run-manifest show <run-id-or-manifest-id>` | Показывает immutable manifest и ledger evidence запуска. |

## Диаграммы

### Composite Flow

```mermaid
flowchart LR
    Seed["Seed: chembl_publication"]
    Input1["crossref_publication · doi, title"]
    Input1 --> Merge
    Input2["openalex_publication · doi, title"]
    Input2 --> Merge
    Input3["pubmed_publication · pmid, doi"]
    Input3 --> Merge
    Input4["semanticscholar_publication · doi, title"]
    Input4 --> Merge
    Merge["Merge: left_outer / seed_priority"]
    Validate["Cross-validation: True"]
    Excluded["Quarantine / nullification"]
    Gold["Gold: composite_publication"]
    Seed --> Merge --> Validate
    Validate -->|valid| Gold
    Validate -->|excluded| Excluded
```

## Owner-approved context

Build a provider-qualified publication view from the ChEMBL seed and publication enrichers.

## Evidence

- `composite_config`: `configs/composites/publication.yaml`
- `effective_entity_config`: `configs/entities/composite/publication.yaml`
- `gold_contract`: `configs/contracts/composite/publication.yaml`
- `composite_cli`: `src/bioetl/interfaces/cli/commands/run_composite.py`
- `quarantine_cli`: `src/bioetl/interfaces/cli/commands/quarantine.py`
