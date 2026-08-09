______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# ChEMBL Error Handling Flow

- Исходная диаграмма: `providers/chembl/04-error-handling-flow.mmd`

## Описание

Диаграмма ChEMBL Error Handling Flow показывает стратегию обработки ошибок для ChEMBL provider на уровне System и использует нотацию flowchart. Материал помогает понять классификацию ошибок, retry логику, circuit breaker и alerting в рамках сценария ChEMBL error handling. В исходном файле прямо зафиксирован контекст: Error handling flow diagram for ChEMBL provider showing API errors, validation failures, DQ threshold breaches, retry logic, and circuit breaker activation. Covers ChEMBL-specific error handling patterns. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Error Classification, API Error Handling, Validation Error Handling, DQ Error Handling, Storage Error Handling, Circuit Breaker, Error Handling Strategy, Alerting. Именно через эти блоки визуализированы этапы обработки ошибок и маршруты передачи управления. Примеры узлов, отражающих доменную модель и инфраструктуру: Detect Error Type, Rate Limit Error, Server Error, Authentication Error, Schema Validation Error, Completeness Error, Circuit Breaker Open, Transient Error, Permanent Error, Apply Retry Strategy, Generate Alert. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-032: Unified HTTP Client
- ADR-016: Error Handling Strategy
- ADR-040: Diagram Governance

## Компоненты

### Error Classification
- Detect Error Type
- Error Category: API Error, Validation Error, DQ Error, Storage Error

### API Error Handling
- HTTP Status handling: 429 Rate Limit, 5xx Server, 4xx Client, Network Error
- Retry logic с backoff для transient errors
- Authentication Error (401), Resource Not Found (404)

### Validation Error Handling
- Schema Validation Error
- Field Validation Error
- Type Validation Error

### DQ Error Handling
- Completeness Error
- Accuracy Error
- Consistency Error

### Storage Error Handling
- Write Error
- Read Error
- Delta Lake Error

### Circuit Breaker
- Check Circuit Breaker State: OPEN, HALF-OPEN, CLOSED
- Circuit Breaker Half-Open check
- Circuit Breaker Open failure

### Error Handling Strategy
- Classify Error Severity: Transient, Permanent, Unknown
- Apply Retry Strategy для transient errors
- No Retry для permanent errors
- Unknown Strategy для unknown errors

### Alerting
- Generate Alert по severity: Critical, Warning, Info
- Log Error Details
- Emit Error Metrics