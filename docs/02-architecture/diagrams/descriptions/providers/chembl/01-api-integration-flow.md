______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# ChEMBL API Integration Flow

- Исходная диаграмма: `providers/chembl/01-api-integration-flow.mmd`

## Описание

Диаграмма ChEMBL API Integration Flow показывает процесс интеграции с ChEMBL API на уровне System и использует нотацию flowchart. Материал помогает понять последовательность шагов интеграции, обработку ошибок, пагинацию и rate limiting в рамках сценария ChEMBL API integration. В исходном файле прямо зафиксирован контекст: API integration flow diagram for ChEMBL provider showing authentication, request construction, pagination handling, rate limiting, and response parsing. Covers ChEMBL-specific API integration patterns. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Authentication Setup, Request Construction, Pagination Setup, Rate Limit Check, HTTP Request Execution, Response Parsing, Error Handling. Именно через эти блоки визуализированы этапы интеграции и маршруты передачи управления. Примеры узлов, отражающих доменную модель и инфраструктуру: Initialize ChEMBL Adapter, Configure API Key, Activity Endpoint, Cursor Pagination, Execute HTTP Request, Parse Response, Create ChEMBL Domain Entity. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-032: Unified HTTP Client
- ADR-010: Local-Only Deployment
- ADR-040: Diagram Governance

## Компоненты

### Authentication Setup
- Проверка наличия API ключа
- Конфигурация API ключа или режим без аутентификации

### Request Construction
- Выбор типа endpoint (Activity, Target, Compound, Assay)
- Построение параметров запроса

### Pagination Setup
- Поддержка различных типов пагинации (Cursor, Offset, Scroll)
- Управление переходом между страницами

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
