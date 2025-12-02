# 05 Parent Enrichment Result

## Описание

`ParentEnrichmentResult` — dataclass-результат, возвращаемый после выполнения этапа обогащения родительских идентификаторов. Включает обработанный DataFrame и сводные показатели (`ParentLookupStats`).

## Модуль

`src/bioetl/library/pipelines/testitem/catalog.py`

## Наследование

Класс наследуется от `object` и представляет собой dataclass для хранения результатов обогащения.

## Основные поля

Dataclass содержит следующие поля:

- `dataframe` — обработанный DataFrame с добавленными родительскими идентификаторами
- `stats` — объект `ParentLookupStats` со статистикой обогащения
- `enrichment_mapping` — соответствие child → parent после обогащения

## Использование

Результат возвращается после выполнения обогащения родительских идентификаторов:

```python
from bioetl.library.pipelines.testitem.catalog import ParentEnrichmentResult

result: ParentEnrichmentResult = enrich_parent_ids(preparation)
print(f"Added {result.stats.added_count} parent IDs")
```

## Related Components

- **ParentEnrichmentPreparation**: подготовительные данные (см. `docs/02-pipelines/chembl/testitem/04-parent-enrichment-preparation.md`)
- **ParentLookupStats**: статистика обогащения (см. `docs/02-pipelines/chembl/testitem/07-parent-lookup-stats.md`)

