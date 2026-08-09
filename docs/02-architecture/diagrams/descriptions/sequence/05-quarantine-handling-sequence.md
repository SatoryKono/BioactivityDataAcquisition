______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Quarantine Handling Sequence

- Исходная диаграмма: `sequence/05-quarantine-handling-sequence.mmd`

## Описание

Диаграмма Quarantine Handling Sequence показывает sequence flow quarantine handling с quarantine routing, inspection, replay и cleanup на уровне System и использует нотацию sequenceDiagram. Материал помогает понять quarantine process, operator inspection и replay mechanisms в рамках сценария quarantine handling. В исходном файле прямо зафиксирован контекст: Sequence diagram showing quarantine handling flow with quarantine routing, inspection, replay, and cleanup. Covers quarantine process and operator intervention. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые участники (participants) включают: DQ Validator, Quarantine Router, Quarantine Storage, Operator Interface, Replay Service, Cleanup Service, Metrics/Tracing. Именно через эти участники визуализированы этапы quarantine handling и маршруты передачи сообщений. Примеры участников, отражающих доменную модель и инфраструктуру: Quarantine Router (routing decision), Quarantine Storage (quarantine data storage), Operator Interface (operator inspection), Replay Service (data replay), Cleanup Service (quarantine cleanup). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `sequence`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-040: Diagram Governance

## Участники

### DQ Validator
- Определяет quarantine routing
- Отправляет quarantine decision

### Quarantine Router
- Управляет quarantine routing
- Решает о quarantine storage
- Координирует quarantine handling

### Quarantine Storage
- Хранит quarantine данные
- Предоставляет доступ к quarantine data
- Управляет quarantine metadata

### Operator Interface
- Предоставляет operator inspection
- Позволяет operator review quarantine data
- Управляет replay decisions

### Replay Service
- Выполняет data replay
- Повторно обрабатывает quarantine данные
- Управляет replay logic

### Cleanup Service
- Выполняет quarantine cleanup
- Удаляет устаревшие quarantine данные
- Управляет retention policies

### Metrics/Tracing
- Эмитирует quarantine metrics
- Управляет quarantine spans
- Обеспечивает observability для quarantine handling

## Sequence Flow

### Quarantine Routing
- DQ Validator → Quarantine Router: quarantine decision
- Quarantine Router → Metrics/Tracing: quarantine metrics
- Quarantine Router → Quarantine Storage: store quarantine data

### Quarantine Storage
- Quarantine Storage хранит quarantine data
- Quarantine Storage → Quarantine Router: storage confirmation
- Quarantine Storage → Metrics/Tracing: storage metrics

### Operator Inspection
- Operator Interface → Quarantine Storage: request quarantine data
- Quarantine Storage → Operator Interface: quarantine data
- Operator просматривает quarantine data
- Operator Interface → Operator Interface: inspection decision

### Replay Decision
- Operator Interface → Replay Service: replay request
- Replay Service → Quarantine Storage: retrieve quarantine data
- Quarantine Storage → Replay Service: quarantine data
- Replay Service выполняет data replay
- Replay Service → Metrics/Tracing: replay metrics

### Replay Execution
- Replay Service обрабатывает quarantine data
- Replay Service → DQ Validator: re-validated data
- DQ Validator → Replay Service: validation result
- Replay Service → Quarantine Storage: update quarantine status

### Cleanup Operations
- Cleanup Service → Quarantine Storage: request cleanup
- Quarantine Storage → Cleanup Service: quarantine metadata
- Cleanup Service применяет retention policies
- Cleanup Service → Quarantine Storage: delete outdated data
- Cleanup Service → Metrics/Tracing: cleanup metrics