# ValidationService

**Модуль:** `src/bioetl/validation/service.py`

Сервис, инкапсулирующий логику валидации данных. Использует `SchemaRegistry` и Pandera для проверки DataFrame.

## Функции

### 1. Валидация структуры
Проверяет соответствие типов данных, наличие обязательных колонок и отсутствие лишних (если схема строгая).

### 2. Валидация данных
Проверяет значения в колонках:
- Regex-паттерны для идентификаторов (например, `^CHEMBL\d+$`).
- Диапазоны значений (например, `pchembl_value` от 0 до 15).
- Допустимые значения (Enum/Check).

### 3. Нормализация порядка
Переупорядочивает колонки DataFrame в соответствии с `column_order` из реестра.

## Интерфейс

```python
class ValidationService:
    def validate(
        self, 
        df: pd.DataFrame, 
        entity_name: str
    ) -> pd.DataFrame:
        """
        Валидирует df по схеме для entity_name.
        Возвращает валидированный (и, возможно, переупорядоченный) DataFrame.
        Бросает SchemaError при ошибке.
        """
```

## Интеграция в Pipeline

`PipelineBase` вызывает `validate()` после стадии трансформации.

```python
# Внутри PipelineBase.run()
df_validated = self.validation_service.validate(df_transformed, self.entity_name)
```

