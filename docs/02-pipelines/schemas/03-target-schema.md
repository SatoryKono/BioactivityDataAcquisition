# 03 Target Schema

## Описание

`TargetSchema` — Pandera-схема DataFrame для сущности *target*. Определяет структуру выходного набора данных target: список обязательных столбцов (`target_id`, `pref_name`, `organism`, `target_type`, `business_key`, `business_key_hash`, `row_hash`) с их типами и условиями (например, `target_id` не nullable и т.д.). Используется для проверки и валидирования данных на стадии *validate*.

## Модуль

`src/bioetl/core/schemas/target_schema.py`

## Наследование

Класс наследуется от `pa.DataFrameSchema` (Pandera).

## Структура схемы

Схема определяет следующие обязательные столбцы:

- `target_id` — идентификатор target (не nullable)
- `pref_name` — предпочтительное название
- `organism` — организм
- `target_type` — тип target
- `business_key` — бизнес-ключ для дедупликации
- `business_key_hash` — хеш бизнес-ключа
- `row_hash` — хеш строки для проверки целостности

## Валидация

Схема используется для валидации DataFrame на стадии *validate* пайплайна. Проверяет:

- Наличие всех обязательных столбцов
- Соответствие типов данных
- Условия на значения (nullable, диапазоны и т.д.)

## Использование

Схема используется в `ChemblTargetPipeline` для валидации данных:

```python
schema = TargetSchema()
validated_df = schema.validate(df)
```

## Related Components

- **DefaultValidationService**: сервис валидации (см. `docs/02-pipelines/core/06-validation-service.md`)
- **ChemblTargetPipeline**: использует схему для валидации данных (см. `docs/02-pipelines/chembl/target/00-target-chembl-overview.md`)

