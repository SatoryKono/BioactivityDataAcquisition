______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# DQ Validation Sequence

- Исходная диаграмма: `sequence/04-dq-validation-sequence.mmd`

## Описание

Диаграмма DQ Validation Sequence показывает sequence flow data quality validation с completeness, accuracy, consistency checks на уровне System и использует нотацию sequenceDiagram. Материал помогает понять DQ validation process, threshold breaches и quarantine routing в рамках сценария data quality validation. В исходном файле прямо зафиксирован контекст: Sequence diagram showing data quality validation flow with completeness, accuracy, consistency checks, threshold breaches, and quarantine routing. Covers DQ validation process. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые участники (participants) включают: Data Ingestion, DQ Validator, Completeness Checker, Accuracy Checker, Consistency Checker, Threshold Monitor, Quarantine Router, Metrics/Tracing. Именно через эти участники визуализированы этапы DQ validation и маршруты передачи сообщений. Примеры участников, отражающих доменную модель и инфраструктуру: DQ Validator (orchestration), Completeness Checker (completeness validation), Accuracy Checker (accuracy validation), Consistency Checker (consistency validation), Threshold Monitor (threshold breaches), Quarantine Router (quarantine routing). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `sequence`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-040: Diagram Governance

## Участники

### Data Ingestion
- Предоставляет данные для DQ validation
- Отправляет data batch

### DQ Validator
- Оркестрирует DQ validation process
- Координирует completeness, accuracy, consistency checks
- Управляет validation results

### Completeness Checker
- Проверяет completeness данных
- Вычисляет completeness metrics
- Определяет completeness breaches

### Accuracy Checker
- Проверяет accuracy данных
- Вычисляет accuracy metrics
- Определяет accuracy breaches

### Consistency Checker
- Проверяет consistency данных
- Вычисляет consistency metrics
- Определяет consistency breaches

### Threshold Monitor
- Мониторит DQ threshold breaches
- Определяет severity breaches
- Генерирует breach alerts

### Quarantine Router
- Управляет quarantine routing
- Решает о routing данных
- Координирует quarantine handling

### Metrics/Tracing
- Эмитирует DQ metrics
- Управляет DQ validation spans
- Обеспечивает observability для DQ validation

## Sequence Flow

### DQ Validation Initialization
- Data Ingestion → DQ Validator: data batch
- DQ Validator → Metrics/Tracing: validation start metrics

### Completeness Validation
- DQ Validator → Completeness Checker: completeness check
- Completeness Checker вычисляет completeness metrics
- Completeness Checker → DQ Validator: completeness results

### Accuracy Validation
- DQ Validator → Accuracy Checker: accuracy check
- Accuracy Checker вычисляет accuracy metrics
- Accuracy Checker → DQ Validator: accuracy results

### Consistency Validation
- DQ Validator → Consistency Checker: consistency check
- Consistency Checker вычисляет consistency metrics
- Consistency Checker → DQ Validator: consistency results

### Threshold Monitoring
- DQ Validator → Threshold Monitor: validation results
- Threshold Monitor проверяет threshold breaches
- Threshold Monitor → DQ Validator: breach status

### Quarantine Routing
- DQ Validator → Quarantine Router: routing decision
- Quarantine Router решает о routing данных
- Quarantine Router → DQ Validator: routing result

### Validation Completion
- DQ Validator → Metrics/Tracing: validation complete metrics
- DQ Validator → Data Ingestion: validation result