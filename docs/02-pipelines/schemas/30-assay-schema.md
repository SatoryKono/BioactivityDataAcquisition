# 30 Assay Schema

## Описание

`AssaySchema` — схема валидации данных ассая (Pandera DataFrameSchema). Определяет обязательные колонки (`assay_id`, `business_key` и др.) и их типы, используется для проверки целостности и приведения типов данных после трансформации.

## Модуль

`src/bioetl/core/schemas/assay_schema.py`

## Наследование

Схема наследуется от `pa.DataFrameSchema` (Pandera) и определяет структуру данных assay.

## Обязательные поля

Схема определяет следующие обязательные поля:

- `assay_id` — идентификатор assay в ChEMBL
- `business_key` — бизнес-ключ для идентификации assay
- `assay_type` — тип assay
- `assay_class` — класс assay
- `target_chembl_id` — идентификатор target в ChEMBL
- И другие поля согласно спецификации

## Использование

Схема используется для валидации результатов пайплайна `ChemblAssayPipeline`:

```python
from bioetl.core.schemas.assay_schema import AssaySchema

validated_df = AssaySchema.validate(df)
```

## Related Components

- **ChemblAssayPipeline**: использует схему для валидации данных (см. `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md`)
- **DefaultValidationService**: использует схему для валидации (см. `docs/02-pipelines/06-validation-service.md`)

