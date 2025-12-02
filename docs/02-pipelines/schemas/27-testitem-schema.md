# 27 TestItem Schema

## Описание

`TestItemSchema` — Pandera-схема валидации для данных тестового элемента. Описывает набор обязательных полей и типы данных для **Test Item**.

## Модуль

`src/bioetl/core/schemas/testitem_schema.py`

## Наследование

Схема наследуется от `pa.DataFrameSchema` (Pandera) и определяет структуру данных тестовых элементов.

## Обязательные поля

Схема определяет следующие обязательные поля:

- `molecule_chembl_id` — идентификатор молекулы в ChEMBL
- `inchi_key` — InChI ключ молекулы
- `canonical_smiles` — канонический SMILES
- `molecular_weight` — молекулярная масса
- И другие поля согласно спецификации

## Использование

Схема используется для валидации результатов пайплайна `TestItemChemblPipeline`:

```python
from bioetl.core.schemas.testitem_schema import TestItemSchema

validated_df = TestItemSchema.validate(df)
```

## Related Components

- **TestItemChemblPipeline**: использует схему для валидации данных (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)
- **DefaultValidationService**: использует схему для валидации (см. `docs/02-pipelines/06-validation-service.md`)

