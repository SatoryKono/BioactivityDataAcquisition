# 07 Parent Lookup Stats

## Описание

`ParentLookupStats` — неизменяемый dataclass для сбора статистики по добавлению родительских идентификаторов: источник данных (кеш/lookup), число отсутствующих, добавленных, не найденных и другие метрики.

## Модуль

`src/bioetl/library/pipelines/testitem/catalog.py`

## Наследование

Класс наследуется от `object` и представляет собой frozen dataclass для хранения статистики.

## Основные поля

Dataclass содержит следующие поля:

- `source` — источник данных (cache, lookup, api)
- `missing_count` — число отсутствующих родительских ID
- `added_count` — число добавленных родительских ID
- `not_found_count` — число не найденных родительских ID
- `cache_hits` — число попаданий в кэш
- `cache_misses` — число промахов кэша

## Использование

Статистика собирается в процессе обогащения родительских идентификаторов:

```python
from bioetl.library.pipelines.testitem.catalog import ParentLookupStats

stats = ParentLookupStats(
    source="api",
    missing_count=10,
    added_count=90,
    not_found_count=5,
    cache_hits=50,
    cache_misses=40
)
```

## Related Components

- **ParentEnrichmentResult**: результат обогащения (см. `docs/02-pipelines/chembl/testitem/05-parent-enrichment-result.md`)
- **ParentLookupPreparedData**: подготовленные данные (см. `docs/02-pipelines/chembl/testitem/06-parent-lookup-prepared-data.md`)

