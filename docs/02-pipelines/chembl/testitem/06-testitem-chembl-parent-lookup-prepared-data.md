# 06 TestItem ChEMBL Parent Lookup Prepared Data

## Описание

`ParentLookupPreparedData` — именованный кортеж (NamedTuple), хранящий заранее подготовленные наборы данных для поиска родительских ID (список исходных **child**-идентификаторов, уже известных родителей и требующих поиска).

## Модуль

`src/bioetl/library/pipelines/testitem/catalog.py`

## Наследование

Класс наследуется от `NamedTuple` и представляет собой неизменяемую структуру данных.

## Основные поля

NamedTuple содержит следующие поля:

- `child_ids` — список исходных child-идентификаторов
- `known_parents` — словарь уже известных соответствий child → parent
- `ids_to_lookup` — список идентификаторов, требующих поиска родительских ID

## Использование

Используется для подготовки данных перед поиском родительских идентификаторов:

```python
from bioetl.library.pipelines.testitem.catalog import ParentLookupPreparedData

prepared = ParentLookupPreparedData(
    child_ids=["CHEMBL1", "CHEMBL2"],
    known_parents={"CHEMBL1": "CHEMBL_PARENT_1"},
    ids_to_lookup=["CHEMBL2"]
)
```

## Related Components

- **ParentEnrichmentPreparation**: подготовительные данные (см. `docs/02-pipelines/chembl/testitem/04-testitem-chembl-parent-enrichment-preparation.md`)
- **ParentLookupStats**: статистика обогащения (см. `docs/02-pipelines/chembl/testitem/07-testitem-chembl-parent-lookup-stats.md`)

