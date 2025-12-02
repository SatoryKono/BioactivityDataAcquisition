# 26 Document Schema

## Описание

`DocumentSchema` — схема данных документов ChEMBL для валидации результирующего DataFrame. Определяет обязательные поля документа (`document_id`, `doi`, `title`, `journal`, и др.) и их типы, используясь для проверки выходного набора данных пайплайна.

## Модуль

`src/bioetl/core/schemas/document_schema.py`

## Наследование

Схема наследуется от `pa.DataFrameSchema` (Pandera) и определяет структуру данных документов.

## Обязательные поля

Схема определяет следующие обязательные поля:

- `document_id` — идентификатор документа
- `doi` — Digital Object Identifier
- `title` — заголовок документа
- `journal` — название журнала
- И другие поля согласно спецификации

## Использование

Схема используется для валидации результатов пайплайна `ChemblDocumentPipeline`:

```python
from bioetl.core.schemas.document_schema import DocumentSchema

validated_df = DocumentSchema.validate(df)
```

## Related Components

- **ChemblDocumentPipeline**: использует схему для валидации данных (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)
- **DefaultValidationService**: использует схему для валидации (см. `docs/02-pipelines/06-validation-service.md`)

