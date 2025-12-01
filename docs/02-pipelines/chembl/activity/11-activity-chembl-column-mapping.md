# 11 Activity ChEMBL Column Mapping

## Описание

`ColumnMapping` — структура сопоставления колонок для парсера. Определяет соответствие между именем результирующей колонки и одним или несколькими путями/ключами в исходном JSON от ChEMBL. Например, `ColumnMapping("activity_id", ("activity_id", "activity_chembl_id"))` означает, что значение для колонки `activity_id` берётся из поля `activity_id` (или альтернативно `activity_chembl_id`) в ответе API.

## Модуль

`bioetl/clients/chembl` (утилиты разбора JSON)

## Структура

ColumnMapping является dataclass и содержит следующие поля:

- `column_name: str` — имя результирующей колонки в DataFrame
- `source_keys: tuple[str, ...]` — tuple возможных исходных ключей в JSON (проверяются по порядку)

## Использование

Маппинги используются в `ActivityParser` для:

- Сопоставления полей JSON с колонками DataFrame
- Поддержки альтернативных ключей в JSON
- Обработки различных форматов ответов API

## Пример

```python
mapping = ColumnMapping(
    column_name="activity_id",
    source_keys=("activity_id", "activity_chembl_id")
)
# Парсер попытается найти значение сначала в "activity_id",
# затем в "activity_chembl_id" если первое отсутствует
```

## Related Components

- **ActivityParser**: использует маппинги для преобразования JSON в DataFrame (см. `docs/02-pipelines/chembl/activity/04-activity-chembl-parser.md`)

