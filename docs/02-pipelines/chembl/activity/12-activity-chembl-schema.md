# 12 Activity ChEMBL Schema

## Описание

`ChEMBLActivitySchema` — валидирующая схема Pandera для данных активности ChEMBL. Описывает все ожидаемые колонки итогового DataFrame и их типы (строка, число, булево и т.д.), а также отмечает обязательные поля. Используется для проверки соответствия выходных данных ожидаемой структуре и для настройки детерминизма сортировки и хэширования ключей при сохранении.

## Модуль

`bioetl/schemas/chembl_activity_schema.py`

## Структура

Схема наследуется от `pandera.pandas.DataFrameSchema` и определяет:

- **Колонки**: все ожидаемые колонки DataFrame с их типами
- **Обязательные поля**: колонки, которые не могут быть NULL
- **Валидация типов**: проверка соответствия типов данных
- **Дополнительные проверки**: диапазоны значений, форматы и т.д.

## Использование

### Валидация данных

```python
from bioetl.schemas.chembl_activity_schema import ChEMBLActivitySchema

# Валидация DataFrame
validated_df = ChEMBLActivitySchema.validate(df)
```

### Регистрация в реестре

Схема регистрируется в `SchemaRegistry` пайплайном для использования при записи результатов:

```python
registry.register(SchemaRegistryEntry(
    identifier="chembl_activity",
    schema=ChEMBLActivitySchema,
    column_order=ChEMBLActivitySchema.columns.keys(),
    business_key=["activity_id"]
))
```

## Детерминизм

Схема обеспечивает детерминизм данных:

- Фиксированный порядок колонок
- Стабильные типы данных
- Валидация бизнес-ключей

## Related Components

- **SchemaRegistry**: реестр схем для валидации (см. `docs/02-pipelines/core/05-schema-registry.md`)
- **UnifiedOutputWriter**: использует схему для валидации перед записью (см. `docs/02-pipelines/core/04-unified-output-writer.md`)
- **DefaultValidationService**: использует схему для валидации данных (см. `docs/02-pipelines/core/06-validation-service.md`)

