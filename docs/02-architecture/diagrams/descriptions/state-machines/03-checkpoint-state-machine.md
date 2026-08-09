______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Checkpoint State Machine

- Исходная диаграмма: `state-machines/03-checkpoint-state-machine.mmd`

## Описание

Диаграмма Checkpoint State Machine показывает state machine для checkpoint management включая checkpoint creation, checkpoint validation, checkpoint restore, checkpoint failure на уровне System и использует нотацию stateDiagram-v2. Материал помогает понять checkpoint state management в рамках сценария checkpoint handling. В исходном файле прямо зафиксирован контекст: State machine diagram showing checkpoint state transitions including checkpoint creation, validation, restore, and failure. Covers checkpoint state management. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые состояния (states) включают: No Checkpoint, Checkpoint Creating, Checkpoint Valid, Checkpoint Invalid, Checkpoint Restoring, Checkpoint Restored, Checkpoint Failed. Именно через эти состояния визуализированы checkpoint lifecycle и state transitions. Примеры состояний, отражающих доменную модель и инфраструктуру: No Checkpoint (initial state), Checkpoint Creating (checkpoint creation), Checkpoint Valid (valid checkpoint), Checkpoint Invalid (invalid checkpoint), Checkpoint Restoring (checkpoint restore), Checkpoint Restored (restored checkpoint), Checkpoint Failed (failed checkpoint). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `state`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-040: Diagram Governance

## Состояния

### No Checkpoint
- Начальное состояние без checkpoint
- Checkpoint не существует
- Переход в Checkpoint Creating при checkpoint creation

### Checkpoint Creating
- Checkpoint создаётся
- Запись checkpoint data
- Переход в Checkpoint Valid при успешном создании
- Переход в Checkpoint Failed при ошибке создания

### Checkpoint Valid
- Checkpoint валиден
- Checkpoint готов к использованию
- Переход в Checkpoint Restoring при checkpoint restore
- Переход в Checkpoint Invalid при validation failure

### Checkpoint Invalid
- Checkpoint невалиден
- Checkpoint не может быть использован
- Переход в No Checkpoint при cleanup

### Checkpoint Restoring
- Checkpoint восстанавливается
- Чтение checkpoint data
- Переход в Checkpoint Restored при успешном восстановлении
- Переход в Checkpoint Failed при ошибке восстановления

### Checkpoint Restored
- Checkpoint успешно восстановлен
- Состояние восстановлено из checkpoint
- Переход в No Checkpoint при продолжении execution

### Checkpoint Failed
- Checkpoint operation failed
- Ошибка при создании или восстановлении
- Переход в No Checkpoint при cleanup

## State Transitions

### Checkpoint Creation
- No Checkpoint → Checkpoint Creating: checkpoint creation
- Checkpoint Creating → Checkpoint Valid: успешное создание
- Checkpoint Creating → Checkpoint Failed: ошибка создания

### Checkpoint Validation
- Checkpoint Valid → Checkpoint Invalid: validation failure
- Checkpoint Invalid → No Checkpoint: cleanup

### Checkpoint Restore
- Checkpoint Valid → Checkpoint Restoring: checkpoint restore
- Checkpoint Restoring → Checkpoint Restored: успешное восстановление
- Checkpoint Restoring → Checkpoint Failed: ошибка восстановления

### Cleanup
- Checkpoint Restored → No Checkpoint: продолжение execution
- Checkpoint Failed → No Checkpoint: cleanup