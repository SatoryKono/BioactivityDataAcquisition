# Activity ChEMBL Pipeline

**Сущность:** Activity
**Endpoint:** `/activity`
**Класс:** `ChemblActivityPipeline`

## Описание
Извлекает данные о биологической активности веществ. Это центральная сущность базы данных, связывающая молекулы, таргеты и ассаи.

## Трансформация (Transform)

**Класс:** `ActivityTransformer`

1. **Очистка**: Удаление записей с пустыми `standard_value`, если это критично для анализа.
2. **Типизация**: Приведение `standard_value` и `pchembl_value` к `float`.
3. **Обогащение**: Добавление колонки `chembl_release`.

## Схема (Validation)

**Схема:** `ActivitySchema`

- `activity_id`: Обязательное поле, уникальный ключ.
- `standard_value`: Числовое значение.
- `standard_units`: Единицы измерения (nM, uM и т.д.).

## Конфигурация

Файл: `configs/pipelines/chembl/activity.yaml`

```yaml
entity_name: activity
endpoint: /activity
primary_key: activity_id
```

