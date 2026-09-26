______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Lock Acquisition State Machine

- Исходная диаграмма: `state-machines/02-lock-acquisition-state-machine.mmd`

## Описание

Диаграмма Lock Acquisition State Machine показывает state machine для lock acquisition включая lock request, lock available, lock held, lock denied, lock release на уровне System и использует нотацию stateDiagram-v2. Материал помогает понять lock acquisition state management в рамках сценария lock acquisition. В исходном файле прямо зафиксирован контекст: State machine diagram showing lock acquisition state transitions including lock request, lock available, lock held, lock denied, and lock release. Covers lock acquisition state management. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые состояния (states) включают: No Lock, Lock Requested, Lock Acquired, Lock Denied, Lock Released. Именно через эти состояния визуализированы lock acquisition lifecycle и state transitions. Примеры состояний, отражающих доменную модель и инфраструктуру: No Lock (initial state), Lock Requested (pending request), Lock Acquired (lock held), Lock Denied (lock unavailable), Lock Released (lock released). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `state`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-015: Pipeline Services Lifecycle
- ADR-040: Diagram Governance

## Состояния

### No Lock
- Начальное состояние без lock
- Lock не запрошен
- Переход в Lock Requested при lock request

### Lock Requested
- Lock запрошен, ожидание ответа
- Проверка доступности lock
- Переход в Lock Acquired при lock available
- Переход в Lock Denied при lock held

### Lock Acquired
- Lock успешно получен
- Lock held текущим процессом
- Переход в Lock Released при lock release

### Lock Denied
- Lock недоступен
- Lock held другим процессом
- Переход в No Lock после retry или timeout

### Lock Released
- Lock освобождён
- Lock доступен для других процессов
- Переход в No Lock

## State Transitions

### Normal Flow
- No Lock → Lock Requested: lock request
- Lock Requested → Lock Acquired: lock available
- Lock Acquired → Lock Released: lock release
- Lock Released → No Lock: lock cleanup

### Error Handling
- Lock Requested → Lock Denied: lock held
- Lock Denied → No Lock: retry или timeout
- Lock Denied → Lock Requested: retry attempt