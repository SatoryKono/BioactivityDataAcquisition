# 04 TestItem ChEMBL Parent Enrichment Preparation

## Описание

`ParentEnrichmentPreparation` — вспомогательный dataclass, содержащий DataFrame и предварительно рассчитанные данные для привязки родительских молекул (иерархия «child → parent» до обогащения).

## Модуль

`src/bioetl/library/pipelines/testitem/catalog.py`

## Наследование

Класс наследуется от `object` и представляет собой dataclass для хранения подготовительных данных.

## Основные поля

Dataclass содержит следующие поля:

- `dataframe` — DataFrame с данными testitem
- `child_ids` — список идентификаторов дочерних молекул
- `parent_mapping` — предварительно рассчитанное соответствие child → parent
- `prepared_data` — подготовленные данные для поиска родительских ID

## Использование

Используется для подготовки данных перед этапом обогащения родительских идентификаторов:

```python
from bioetl.library.pipelines.testitem.catalog import ParentEnrichmentPreparation

preparation = ParentEnrichmentPreparation(
    dataframe=df,
    child_ids=child_ids,
    parent_mapping=parent_mapping
)
```

## Related Components

- **ParentEnrichmentResult**: результат обогащения (см. `docs/02-pipelines/chembl/testitem/05-testitem-chembl-parent-enrichment-result.md`)
- **ParentLookupStats**: статистика обогащения (см. `docs/02-pipelines/chembl/testitem/07-testitem-chembl-parent-lookup-stats.md`)

