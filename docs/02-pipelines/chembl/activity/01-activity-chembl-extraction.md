# 01 Activity ChEMBL Extraction

## Description

`ActivityExtractor` — класс этапа извлечения данных активности из API ChEMBL. Вызывает клиент ChEMBL батчами и формирует результирующий DataFrame с метаданными. Наследуется от `StageABC` и реализует интерфейс стадии извлечения.

## Module

`src/bioetl/pipelines/chembl/activity/stages.py`

## Inheritance

Класс наследуется от `StageABC` и реализует интерфейс стадии извлечения данных.

## Main Method

### `extract(self, descriptor: ChemblExtractionDescriptor, config: PipelineConfig, batch_size: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]`

Выполняет извлечение данных активности из ChEMBL API.

**Parameters:**
- `descriptor` — дескриптор извлечения с параметрами запроса (IDs, фильтры, пагинация)
- `config` — конфигурация пайплайна
- `batch_size` — размер батча для обработки (опционально)

**Extraction Process:**

1. Построение клиента: создание `ChemblClient` через `_build_client`
2. Выполнение запросов: отправка запросов к ChEMBL API через клиент
3. Парсинг ответов: преобразование JSON-ответов в DataFrame через `ActivityParser`
4. Сборка результатов: объединение данных из всех страниц/батчей в единый DataFrame
5. Метаданные: сбор метаданных о процессе извлечения (количество записей, время выполнения)

**Returns:** кортеж из DataFrame с данными и словаря метаданных.

## Response Parsing

### ActivityParser

`ActivityParser` — утилита для разбора ответов ChEMBL API для данных активности. Преобразует сырые JSON-данные от ChEMBL `/activity` endpoint в нормализованный pandas DataFrame с требуемыми колонками, сопоставляя поля API с именами колонок доменной схемы.

**Module:** `bioetl/pipelines/chembl/activity/parsers.py`

**Main Method:**

#### `parse(self, raw_json: Any) -> pd.DataFrame`

Парсит сырой JSON payload от ChEMBL API и преобразует его в DataFrame.

**Parameters:**
- `raw_json` — сырой JSON-ответ от ChEMBL API

**Parsing Process:**

1. Извлечение записей: использование `build_records_from_payload` для извлечения списка записей из JSON
2. Применение маппингов: использование списка маппингов `_ACTIVITY_MAPPINGS` для сопоставления полей API с колонками DataFrame
3. Формирование DataFrame: создание DataFrame с нужными колонками согласно доменной схеме

**Returns:** DataFrame с нормализованными данными активности.

### Column Mapping

`ColumnMapping` — структура сопоставления колонок для парсера. Определяет соответствие между именем результирующей колонки и одним или несколькими путями/ключами в исходном JSON от ChEMBL.

**Module:** `bioetl/clients/chembl` (утилиты разбора JSON)

**Structure:**

ColumnMapping является dataclass и содержит следующие поля:

- `column_name: str` — имя результирующей колонки в DataFrame
- `source_keys: tuple[str, ...]` — tuple возможных исходных ключей в JSON (проверяются по порядку)

**Usage:**

Маппинги используются в `ActivityParser` для:
- Сопоставления полей JSON с колонками DataFrame
- Поддержки альтернативных ключей в JSON (например, `activity_id` или `activity_chembl_id`)
- Обработки различных форматов ответов API
- Обработки вложенных структур JSON

**Example:**

```python
mapping = ColumnMapping(
    column_name="activity_id",
    source_keys=("activity_id", "activity_chembl_id")
)
# Парсер попытается найти значение сначала в "activity_id",
# затем в "activity_chembl_id" если первое отсутствует
```

## Internal Methods

### `_build_client(self, config: PipelineConfig) -> BaseClient`

Создаёт клиент для работы с ChEMBL API. Использует `client_factory` из конфигурации или создаёт клиент по умолчанию, если фабрика не указана.

### `_fallback_rows(self, ids: list[str], exc: Exception) -> pd.DataFrame`

Создаёт DataFrame-заглушку для указанных IDs в случае ошибки извлечения. Используется для обработки частичных сбоев и сохранения информации о проблемных записях.

## Error Handling

Стадия обрабатывает различные типы ошибок:
- Ошибки сети: повторные попытки через `RetryPolicyABC`
- Ошибки парсинга: логирование и создание заглушек через `_fallback_rows`
- Частичные сбои: продолжение обработки остальных записей

## Extraction Metadata

Метаданные включают:
- Количество извлечённых записей
- Время выполнения извлечения
- Информацию о батчах и страницах
- Ошибки и предупреждения

## Related Components

- **ChemblClient**: REST-клиент для ChEMBL API (см. `docs/02-pipelines/core/01-base-external-data-client.md`)
- **ChemblExtractionDescriptor**: дескриптор параметров извлечения (см. `00-activity-chembl-overview.md`)
- **ColumnMapping**: структура сопоставления колонок (см. выше)
