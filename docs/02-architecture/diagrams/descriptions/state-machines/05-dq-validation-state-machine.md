______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# DQ Validation State Machine

- Исходная диаграмма: `state-machines/05-dq-validation-state-machine.mmd`

## Описание

Диаграмма DQ Validation State Machine показывает state machine для DQ validation включая validation pending, validation executing, validation passed, validation failed, threshold breach, quarantine routing на уровне System и использует нотацию stateDiagram-v2. Материал помогает понять DQ validation state management в рамках сценария DQ validation. В исходном файле прямо зафиксирован контекст: State machine diagram showing DQ validation state transitions including validation pending, executing, passed, failed, threshold breach, and quarantine routing. Covers DQ validation state management. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые состояния (states) включают: No Validation, Validation Pending, Validation Executing, Validation Passed, Validation Failed, Threshold Breach, Quarantine Pending, Quarantine Routed. Именно через эти состояния визуализированы DQ validation lifecycle и state transitions. Примеры состояний, отражающих доменную модель и инфраструктуру: No Validation (initial state), Validation Pending (validation planned), Validation Executing (validation in progress), Validation Passed (validation success), Validation Failed (validation failure), Threshold Breach (threshold exceeded), Quarantine Pending (quarantine planned), Quarantine Routed (quarantine executed). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `state`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-040: Diagram Governance

## Состояния

### No Validation
- Начальное состояние без validation
- Validation не запрошена
- Переход в Validation Pending при validation request

### Validation Pending
- Validation запланирована
- Validation queue
- Переход в Validation Executing для validation execution

### Validation Executing
- Validation выполняется
- DQ checks в progress
- Переход в Validation Passed при успешной validation
- Переход в Validation Failed при неудачной validation
- Переход в Threshold Breach при threshold breach

### Validation Passed
- Validation успешна
- Все DQ checks passed
- Переход в No Validation для следующего batch

### Validation Failed
- Validation неудачна
- DQ checks failed
- Переход в Quarantine Pending для quarantine routing

### Threshold Breach
- Threshold breach detected
- DQ threshold exceeded
- Переход в Quarantine Pending для quarantine routing

### Quarantine Pending
- Quarantine запланирован
- Quarantine routing decision
- Переход в Quarantine Routed для quarantine execution

### Quarantine Routed
- Quarantine выполнен
- Данные направлены в quarantine
- Переход в No Validation для следующего batch

## State Transitions

### Validation Flow
- No Validation → Validation Pending: validation request
- Validation Pending → Validation Executing: validation execution

### Validation Results
- Validation Executing → Validation Passed: успешная validation
- Validation Executing → Validation Failed: неудачная validation
- Validation Executing → Threshold Breach: threshold breach

### Quarantine Routing
- Validation Failed → Quarantine Pending: quarantine planning
- Threshold Breach → Quarantine Pending: quarantine planning
- Quarantine Pending → Quarantine Routed: quarantine execution

### Normal Flow
- Validation Passed → No Validation: следующий batch
- Quarantine Routed → No Validation: следующий batch