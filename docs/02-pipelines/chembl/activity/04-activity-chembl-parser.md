# 04 Activity ChEMBL Parser

## Описание

`ActivityParser` — утилита для разбора ответов ChEMBL API для данных активности. Преобразует сырые JSON-данные от ChEMBL `/activity` endpoint в нормализованный pandas DataFrame с требуемыми колонками, сопоставляя поля API с именами колонок доменной схемы.

## Модуль

`bioetl/pipelines/chembl/activity/parsers.py`

## Основной метод

### `parse(self, raw_json: Any) -> pd.DataFrame`

Парсит сырой JSON payload от ChEMBL API и преобразует его в DataFrame.

**Параметры:**
- `raw_json` — сырой JSON-ответ от ChEMBL API

**Процесс парсинга:**

1. Извлечение записей: использование `build_records_from_payload` для извлечения списка записей из JSON
2. Применение маппингов: использование списка маппингов `_ACTIVITY_MAPPINGS` для сопоставления полей API с колонками DataFrame
3. Формирование DataFrame: создание DataFrame с нужными колонками согласно доменной схеме

**Возвращает:** DataFrame с нормализованными данными активности.

## Маппинг полей

Парсер использует `ColumnMapping` для сопоставления полей API с колонками:

- Определяет соответствие между именем результирующей колонки и путями/ключами в JSON
- Поддерживает альтернативные ключи (например, `activity_id` или `activity_chembl_id`)
- Обрабатывает вложенные структуры JSON

## Related Components

- **ColumnMapping**: структура сопоставления колонок (см. `docs/02-pipelines/chembl/activity/11-activity-chembl-column-mapping.md`)
- **ActivityExtractor**: использует парсер для преобразования ответов API (см. `docs/02-pipelines/chembl/activity/01-activity-chembl-extraction.md`)

