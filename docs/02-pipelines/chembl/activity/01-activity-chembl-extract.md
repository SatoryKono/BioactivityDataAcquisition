# 01 Activity ChEMBL Extract

## Описание

`ActivityExtractor` — стадия Extract для пайплайна ChEMBL Activity. Отвечает за извлечение сырых данных из ChEMBL API и преобразование их в pandas DataFrame. Стадия использует `ChemblClient` для выполнения запросов к API, обрабатывает ответы и собирает данные в структурированный DataFrame.

## Модуль

`bioetl/pipelines/chembl/activity/stages.py`

## Основной метод

### `extract(self, descriptor: ChemblExtractionDescriptor, config: PipelineConfig, batch_size: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]`

Выполняет извлечение данных активности из ChEMBL API.

**Параметры:**
- `descriptor` — дескриптор извлечения с параметрами запроса (IDs, фильтры, пагинация)
- `config` — конфигурация пайплайна
- `batch_size` — размер батча для обработки (опционально)

**Процесс извлечения:**

1. Построение клиента: создание `ChemblClient` через `_build_client`
2. Выполнение запросов: отправка запросов к ChEMBL API через клиент
3. Парсинг ответов: преобразование JSON-ответов в DataFrame через `ActivityParser`
4. Сборка результатов: объединение данных из всех страниц/батчей в единый DataFrame
5. Метаданные: сбор метаданных о процессе извлечения (количество записей, время выполнения)

**Возвращает:** кортеж из DataFrame с данными и словаря метаданных.

## Внутренние методы

### `_build_client(self, config: PipelineConfig) -> BaseClient`

Создаёт клиент для работы с ChEMBL API. Использует `client_factory` из конфигурации или создаёт клиент по умолчанию, если фабрика не указана.

### `_fallback_rows(self, ids: list[str], exc: Exception) -> pd.DataFrame`

Создаёт DataFrame-заглушку для указанных IDs в случае ошибки извлечения. Используется для обработки частичных сбоев и сохранения информации о проблемных записях.

## Обработка ошибок

Стадия обрабатывает различные типы ошибок:
- Ошибки сети: повторные попытки через `RetryPolicyABC`
- Ошибки парсинга: логирование и создание заглушек через `_fallback_rows`
- Частичные сбои: продолжение обработки остальных записей

## Метаданные извлечения

Метаданные включают:
- Количество извлечённых записей
- Время выполнения извлечения
- Информацию о батчах и страницах
- Ошибки и предупреждения

## Related Components

- **ChemblClient**: REST-клиент для ChEMBL API (см. `docs/02-pipelines/01-base-external-data-client.md`)
- **ActivityParser**: парсер ответов ChEMBL API (см. `docs/02-pipelines/chembl/activity/04-activity-chembl-parser.md`)
- **ChemblExtractionDescriptor**: дескриптор параметров извлечения (см. `docs/02-pipelines/chembl/activity/07-activity-chembl-descriptor.md`)

