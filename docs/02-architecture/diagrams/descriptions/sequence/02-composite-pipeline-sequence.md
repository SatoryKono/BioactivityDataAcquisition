______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Composite Pipeline Sequence

- Исходная диаграмма: `sequence/02-composite-pipeline-sequence.mmd`

## Описание

Диаграмма Composite Pipeline Sequence показывает sequence flow выполнения composite pipeline с seed pipeline, enricher coordination, merge operation, conflict resolution и final output на уровне System и использует нотацию sequenceDiagram. Материал помогает понять реализацию ADR-026 composite pipeline pattern в рамках сценария composite pipeline execution. В исходном файле прямо зафиксирован контекст: Sequence diagram showing composite pipeline execution with seed pipeline, enricher coordination, merge operation, conflict resolution, and final output. Covers ADR-026 composite pipeline pattern implementation. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые участники (participants) включают: CLI User, Composite Pipeline Service, Seed Pipeline, Enricher Pipelines, Merge Service, Conflict Resolver, Storage Writer, Metrics/Tracing. Именно через эти участники визуализированы этапы выполнения composite pipeline и маршруты передачи сообщений. Примеры участников, отражающих доменную модель и инфраструктуру: Seed Pipeline (initial data extraction), Enricher Pipelines (data enrichment), Merge Service (merge operation), Conflict Resolver (conflict resolution), Storage Writer (final output). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `sequence`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-026: Composite Pipeline Pattern
- ADR-018: Gold Strict Validation
- ADR-023: Entity Type Patterns
- ADR-040: Diagram Governance

## Участники

### CLI User
- Инициатор composite pipeline execution
- Отправляет команду запуска composite pipeline

### Composite Pipeline Service
- Оркестрирует выполнение composite pipeline
- Координирует seed pipeline и enricher pipelines
- Управляет merge operation

### Seed Pipeline
- Выполняет initial data extraction
- Предоставляет seed данные для enrichment
- Генерирует metrics для seed extraction

### Enricher Pipelines
- Выполняют data enrichment
- Обогащают seed данные дополнительными атрибутами
- Генерируют metrics для enrichment

### Merge Service
- Выполняет merge operation
- Объединяет данные из seed и enricher pipelines
- Управляет merge logic

### Conflict Resolver
- Разрешает конфликты при merge
- Применяет стратегии conflict resolution
- Генерирует metrics для conflict resolution

### Storage Writer
- Записывает final output
- Применяет strict validation (ADR-018)
- Управляет quarantine routing

### Metrics/Tracing
- Эмитирует metrics для всех этапов
- Управляет tracing spans
- Обеспечивает observability для composite pipeline

## Sequence Flow

### Composite Pipeline Initialization
- CLI User → Composite Pipeline Service: команда запуска
- Composite Pipeline Service → Seed Pipeline: инициализация seed pipeline
- Composite Pipeline Service → Enricher Pipelines: инициализация enricher pipelines

### Seed Pipeline Execution
- Seed Pipeline выполняет data extraction
- Seed Pipeline генерирует seed data
- Seed Pipeline → Composite Pipeline Service: seed data ready

### Enricher Pipeline Execution
- Composite Pipeline Service → Enricher Pipelines: запуск enrichment
- Enricher Pipelines выполняют data enrichment
- Enricher Pipelines → Composite Pipeline Service: enriched data ready

### Merge Operation
- Composite Pipeline Service → Merge Service: запуск merge
- Merge Service объединяет seed и enriched данные
- Merge Service → Conflict Resolver: проверка конфликтов

### Conflict Resolution
- Conflict Resolver проверяет наличие конфликтов
- Conflict Resolver применяет стратегии resolution
- Conflict Resolver → Merge Service: resolved data

### Final Output
- Merge Service → Storage Writer: запись final output
- Storage Writer применяет strict validation (ADR-018)
- Storage Writer → Composite Pipeline Service: write result
- Composite Pipeline Service → CLI User: результат выполнения