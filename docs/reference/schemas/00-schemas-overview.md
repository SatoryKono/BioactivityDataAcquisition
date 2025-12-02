# Schemas Overview

В проекте используются схемы Pandera для валидации всех табличных данных.

## Принципы

1. **Strict Validation**: Запрещены лишние колонки, не описанные в схеме.
2. **Explicit Types**: Типы данных (int, float, string) задаются явно.
3. **Checks**: Используются проверки диапазонов (`ge`, `le`), регулярные выражения (`str_matches`) и допустимые значения (`isin`).

## Схемы ChEMBL

### ActivitySchema
- `activity_id`: `int` (PK)
- `pchembl_value`: `float` (nullable, 0-15)
- `standard_value`: `float` (nullable)
- `standard_units`: `str` (nullable)

### AssaySchema
- `assay_chembl_id`: `str` (PK, Regex `^CHEMBL\d+$`)
- `assay_type`: `str` (Category: B, F, A, T, P)

### DocumentSchema
- `document_chembl_id`: `str` (PK)
- `doi`: `str` (nullable, DOI Regex)
- `pubmed_id`: `int` (nullable)

### TargetSchema и TestitemSchema
Аналогично описывают свои сущности.

## Валидация

Валидация происходит на стадии `validate` пайплайна.
При ошибке выбрасывается `pandera.errors.SchemaError` или `SchemaErrors`, содержащие детальную информацию о несоответствиях.

