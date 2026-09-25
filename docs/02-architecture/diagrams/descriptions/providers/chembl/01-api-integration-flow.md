______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-09-25'

______________________________________________________________________

# ChEMBL API Integration Flow

- Исходная диаграмма: `providers/chembl/01-api-integration-flow.mmd`

## Описание

Диаграмма показывает публичный ChEMBL API. Адаптер собирает запрос с `offset` и `limit`. ChEMBL нет в `PROVIDER_AUTH_REQUIREMENTS`, отдельной ветки API key нет. Cursor и scroll пагинация не используются. Дальше идут rate limit, HTTP, разбор JSON и переход на следующую страницу по `page_meta.next`.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-09-24`

## ADR References

- ADR-032: Unified HTTP Client
- ADR-010: Local-Only Deployment
- ADR-040: Diagram Governance

## Компоненты

### Public API
- Публичный ChEMBL API без ветки API key

### Request Construction
- Выбор endpoint: Activity, Target, Compound, Assay
- Параметры запроса `offset` и `limit`

### Pagination
- Только offset/limit
- Следующая страница, если ответ содержит продолжение

### Rate Limit Check
- Проверка rate limit перед выполнением запроса
- Ожидание сброса rate limit при необходимости

### HTTP Request Execution
- Выполнение HTTP запроса к ChEMBL API
- Обработка различных статусов ответа (200 OK, 429 Rate Limit, 5xx Server Error, 4xx Client Error)
- Retry логика с backoff

### Response Parsing
- Валидация формата ответа (JSON)
- Извлечение данных и трансформация в доменную модель
- Создание ChEMBL domain entity

### Error Handling
- Логирование деталей ошибок
- Эмитация error metrics
- Обработка различных типов ошибок
