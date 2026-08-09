______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Pipeline State Machine

- Исходная диаграмма: `state-machines/01-pipeline-state-machine.mmd`

## Описание

Диаграмма Pipeline State Machine показывает state machine для pipeline state transitions включая initial → running → success/failure, retry states, circuit breaker states и cleanup states на уровне System и использует нотацию stateDiagram-v2. Материал помогает понять pipeline lifecycle state management в рамках сценария pipeline state machine. В исходном файле прямо зафиксирован контекст: State machine diagram showing pipeline state transitions including initial → running → success/failure, retry states, circuit breaker states, and cleanup states. Covers pipeline lifecycle state management. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые состояния (states) включают: Initial, Running, Success, Failure, Retry, Circuit Breaker Open, Circuit Breaker Half-Open, Circuit Breaker Closed, Cleanup. Именно через эти состояния визуализированы pipeline lifecycle и state transitions. Примеры состояний, отражающих доменную модель и инфраструктуру: Initial (initial state), Running (active execution), Success (successful completion), Failure (failed execution), Retry (retry logic), Circuit Breaker states (circuit breaker pattern), Cleanup (cleanup operations). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `state`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-015: Pipeline Services Lifecycle
- ADR-010: Local-Only Deployment
- ADR-040: Diagram Governance

## Состояния

### Initial
- Начальное состояние pipeline
- Pipeline инициализирован, но ещё не запущен
- Переход в Running при запуске

### Running
- Активное выполнение pipeline
- Pipeline выполняет extraction, transformation, writes
- Переход в Success при успешном завершении
- Переход в Failure при ошибке
- Переход в Retry при retryable error

### Success
- Успешное завершение pipeline
- Все операции выполнены успешно
- Переход в Cleanup для cleanup operations

### Failure
- Неудачное завершение pipeline
- Pipeline завершился с ошибкой
- Переход в Cleanup для cleanup operations
- Переход в Retry при retryable error

### Retry
- Состояние retry для retryable errors
- Pipeline выполняет retry logic с backoff
- Переход в Running для retry attempt
- Переход в Failure при exhausted retries

### Circuit Breaker Open
- Circuit breaker в открытом состоянии
- Pipeline execution заблокирован
- Переход в Circuit Breaker Half-Open после cooldown

### Circuit Breaker Half-Open
- Circuit breaker в полуоткрытом состоянии
- Pipeline execution разрешён для теста
- Переход в Circuit Breaker Closed при успешном выполнении
- Переход в Circuit Breaker Open при неудачном выполнении

### Circuit Breaker Closed
- Circuit breaker в закрытом состоянии
- Pipeline execution разрешён
- Нормальное состояние для pipeline execution

### Cleanup
- Состояние cleanup operations
- Выполняются cleanup operations
- Переход в Initial после завершения cleanup

## State Transitions

### Normal Flow
- Initial → Running: запуск pipeline
- Running → Success: успешное завершение
- Success → Cleanup: начало cleanup
- Cleanup → Initial: завершение cleanup

### Error Handling
- Running → Failure: неудачное завершение
- Failure → Cleanup: начало cleanup
- Running → Retry: retryable error
- Retry → Running: retry attempt
- Retry → Failure: exhausted retries

### Circuit Breaker
- Running → Circuit Breaker Open: circuit breaker activation
- Circuit Breaker Open → Circuit Breaker Half-Open: cooldown period
- Circuit Breaker Half-Open → Circuit Breaker Closed: successful test
- Circuit Breaker Half-Open → Circuit Breaker Open: failed test
- Circuit Breaker Closed → Running: normal execution