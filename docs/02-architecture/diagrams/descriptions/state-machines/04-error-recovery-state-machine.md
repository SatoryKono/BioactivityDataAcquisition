______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Error Recovery State Machine

- Исходная диаграмма: `state-machines/04-error-recovery-state-machine.mmd`

## Описание

Диаграмма Error Recovery State Machine показывает state machine для error recovery включая error detection, error classification, retry logic, fallback, error escalation на уровне System и использует нотацию stateDiagram-v2. Материал помогает понять error recovery state management в рамках сценария error recovery. В исходном файле прямо зафиксирован контекст: State machine diagram showing error recovery state transitions including error detection, classification, retry logic, fallback, and escalation. Covers error recovery state management. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые состояния (states) включают: No Error, Error Detected, Error Classified, Retry Pending, Retry Executing, Fallback Pending, Fallback Executing, Error Escalated, Error Resolved. Именно через эти состояния визуализированы error recovery lifecycle и state transitions. Примеры состояний, отражающих доменную модель и инфраструктуру: No Error (normal state), Error Detected (error occurrence), Error Classified (error classification), Retry Pending (retry planning), Retry Executing (retry execution), Fallback Pending (fallback planning), Fallback Executing (fallback execution), Error Escalated (error escalation), Error Resolved (error resolution). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `state`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-016: Error Handling Strategy
- ADR-040: Diagram Governance

## Состояния

### No Error
- Нормальное состояние без ошибок
- Система работает корректно
- Переход в Error Detected при error occurrence

### Error Detected
- Ошибка обнаружена
- Error logging и metrics
- Переход в Error Classified для classification

### Error Classified
- Ошибка классифицирована
- Определён error type и severity
- Переход в Retry Pending для retryable errors
- Переход в Fallback Pending для fallbackable errors
- Переход в Error Escalated для critical errors

### Retry Pending
- Retry запланирован
- Retry strategy определён
- Переход в Retry Executing для retry execution

### Retry Executing
- Retry выполняется
- Retry logic с backoff
- Переход в Error Resolved при успешном retry
- Переход в Retry Pending для следующего retry
- Переход в Fallback Pending при exhausted retries

### Fallback Pending
- Fallback запланирован
- Fallback strategy определён
- Переход в Fallback Executing для fallback execution

### Fallback Executing
- Fallback выполняется
- Fallback logic execution
- Переход в Error Resolved при успешном fallback
- Переход в Error Escalated при fallback failure

### Error Escalated
- Ошибка эскалирована
- Alert generation и operator notification
- Переход в Error Resolved при manual resolution

### Error Resolved
- Ошибка разрешена
- Система восстановлена
- Переход в No Error

## State Transitions

### Error Detection
- No Error → Error Detected: error occurrence
- Error Detected → Error Classified: error classification

### Error Classification
- Error Classified → Retry Pending: retryable error
- Error Classified → Fallback Pending: fallbackable error
- Error Classified → Error Escalated: critical error

### Retry Logic
- Retry Pending → Retry Executing: retry execution
- Retry Executing → Error Resolved: успешный retry
- Retry Executing → Retry Pending: следующий retry
- Retry Executing → Fallback Pending: exhausted retries

### Fallback Logic
- Fallback Pending → Fallback Executing: fallback execution
- Fallback Executing → Error Resolved: успешный fallback
- Fallback Executing → Error Escalated: fallback failure

### Error Escalation
- Error Escalated → Error Resolved: manual resolution

### Resolution
- Error Resolved → No Error:恢复正常 operation