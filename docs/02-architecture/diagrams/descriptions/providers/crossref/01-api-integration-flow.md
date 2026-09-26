______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# CrossRef API Integration Flow

- Исходная диаграмма: `providers/crossref/01-api-integration-flow.mmd`

## Описание

Диаграмма CrossRef API Integration Flow показывает процесс интеграции с CrossRef API для извлечения DOI publication metadata на уровне System и использует нотацию flowchart. Материал помогает понять sequence of operations для CrossRef extract, включая rate limiting, circuit breaker, pagination и error handling в рамках сценария CrossRef API integration. В исходном файле прямо зафиксирован контекст: API integration flow for CrossRef (DOI publication metadata). Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: UnifiedHTTPClient, Rate Limit Check, Request Building, HTTP Call, Circuit Breaker, Response Handling, Pagination. Именно через эти блоки визуализированы этапы интеграции и маршруты передачи управления. Примеры узлов, отражающих доменную модель и инфраструктуру: Start CrossRef extract, UnifiedHTTPClient ADR-032, Build request + pagination cursor, HTTP call, Circuit breaker, Parse payload, Hand off records to Bronze writer. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-28`

## ADR References

- ADR-032: Unified HTTP Client
- ADR-010: Local-Only Deployment
- ADR-040: Diagram Governance

## Компоненты

### UnifiedHTTPClient
- Использование UnifiedHTTPClient согласно ADR-032
- Rate limit check с backoff/wait при необходимости

### Request Building
- Построение запроса с pagination cursor
- Управление пагинацией для многостраничных результатов

### HTTP Call & Circuit Breaker
- Выполнение HTTP вызова
- Circuit breaker check (Open/Closed states)
- Retry логика с jitter для transient errors

### Response Handling
- Обработка различных классов ответов (2xx, 429/5xx, 4xx permanent)
- Parse payload для успешных ответов
- Error path / quarantine upstream для permanent errors

### Pagination
- Проверка наличия дополнительных страниц
- Циклический возврат к Request Building для следующей страницы
- Hand off records to Bronze writer при завершении