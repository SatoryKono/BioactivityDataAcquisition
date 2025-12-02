# 05 Schema Registry

## Описание

`SchemaRegistry` — in-memory реестр схем данных для ETL-пайплайнов. Хранит типизированные схемы (например, Pandera `DataFrameSchema`) для различных сущностей пайплайнов, обеспечивая централизованный доступ к схемам валидации, метаданным схем (версия, описание) и дополнительным настройкам (порядок колонок, обязательные поля, бизнес-ключи, хеши строк).

Реестр используется `UnifiedOutputWriter` для валидации данных перед записью и обеспечения соответствия структуры данных зарегистрированным схемам.

## Модуль

`src/bioetl/core/io/artifacts.py`

## Основные возможности

- **Централизованное хранение**: единая точка доступа к схемам валидации
- **Типизированные схемы**: поддержка Pandera `DataFrameSchema` и других типов схем
- **Метаданные схем**: версия, описание, порядок колонок
- **Бизнес-ключи**: регистрация бизнес-ключей для дедупликации
- **Хеши строк**: поддержка хеш-столбцов для проверки целостности

## Основные методы

### `register(self, entry: SchemaRegistryEntry) -> None`

Регистрирует схему в реестре. Если схема с таким идентификатором уже зарегистрирована или нарушен порядок колонок (`column_order`), выбрасывается исключение.

**Параметры:**
- `entry` — объект `SchemaRegistryEntry` с информацией о схеме

**Валидация при регистрации:**
- Проверка уникальности идентификатора схемы
- Проверка соответствия `column_order` схеме
- Валидация структуры схемы

### `get(self, identifier: str) -> SchemaRegistryEntry`

Получает зарегистрированную схему по идентификатору. Выбрасывает `KeyError`, если схема не найдена.

**Параметры:**
- `identifier` — идентификатор схемы (например, `"chembl_activity"`)

**Возвращает:** объект `SchemaRegistryEntry` с полной информацией о схеме.

## Структура SchemaRegistryEntry

Запись в реестре содержит:

- `identifier: str` — уникальный идентификатор схемы
- `schema: DataFrameSchema` — Pandera-схема для валидации
- `version: str` — версия схемы
- `description: str` — описание схемы
- `column_order: list[str]` — порядок колонок для детерминированной записи
- `business_key: list[str]` — список колонок, образующих бизнес-ключ
- `row_hash_column: str | None` — имя колонки с хешем строки

## Использование

### Регистрация схемы

```python
from bioetl.core.io.artifacts import SchemaRegistry, SchemaRegistryEntry
from bioetl.schemas.chembl_activity_schema import ChEMBLActivitySchema

registry = SchemaRegistry()

entry = SchemaRegistryEntry(
    identifier="chembl_activity",
    schema=ChEMBLActivitySchema,
    version="1.0",
    description="Schema for ChEMBL activity data",
    column_order=ChEMBLActivitySchema.columns.keys(),
    business_key=["activity_id"],
    row_hash_column="hash_row"
)

registry.register(entry)
```

### Получение схемы

```python
# Получение схемы для валидации
entry = registry.get("chembl_activity")
schema = entry.schema

# Валидация DataFrame
validated_df = schema.validate(df)
```

## Интеграция с пайплайнами

Пайплайны регистрируют свои схемы при инициализации:

```python
class ChemblActivityPipeline:
    def _build_schema_registry(self) -> SchemaRegistry:
        registry = SchemaRegistry()
        
        # Регистрация схемы активности
        activity_entry = SchemaRegistryEntry(
            identifier="chembl_activity",
            schema=ChEMBLActivitySchema,
            # ... другие параметры
        )
        registry.register(activity_entry)
        
        return registry
```

## Related Components

- **ChEMBLActivitySchema**: Pandera-схема для данных активности ChEMBL (см. `docs/02-pipelines/chembl/activity/06-activity-chembl-schema.md`)
- **UnifiedOutputWriter**: использует реестр для валидации данных перед записью (см. `docs/02-pipelines/core/04-unified-output-writer.md`)
- **DefaultValidationService**: использует схемы из реестра для валидации (см. `docs/02-pipelines/core/06-validation-service.md`)

