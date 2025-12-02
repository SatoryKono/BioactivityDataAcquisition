# 28 Testitems Schema

## Описание

`TestitemsSchema` — Pandera-схема для полного набора тестовых элементов (DataFrame). Используется для проверки итоговой таблицы **Test Item** – наличие обязательных колонок (например, `molecule_chembl_id`) и корректности типов.

## Модуль

`src/bioetl/library/schemas/testitems.py`

## Наследование

Схема наследуется от `pa.DataFrameSchema` (Pandera) и определяет структуру полного набора тестовых элементов.

## Обязательные поля

Схема определяет следующие обязательные поля:

- `molecule_chembl_id` — идентификатор молекулы в ChEMBL (обязательное поле)
- `inchi_key` — InChI ключ молекулы
- `canonical_smiles` — канонический SMILES
- `molecular_weight` — молекулярная масса
- И другие поля согласно спецификации

## Использование

Схема используется для валидации итогового DataFrame с тестовыми элементами:

```python
from bioetl.library.schemas.testitems import TestitemsSchema

validated_df = TestitemsSchema.validate(df)
```

## Отличия от TestItemSchema

- `TestitemsSchema` — для валидации полного набора (множественное число)
- `TestItemSchema` — для валидации отдельного элемента (единственное число)

## Related Components

- **TestItemSchema**: схема для отдельного элемента (см. `docs/02-pipelines/schemas/27-testitem-schema.md`)
- **TestItemChemblPipeline**: использует схему для валидации данных (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)

