______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Pipeline Execution Sequence

- Исходная диаграмма: `sequence/01-pipeline-execution-sequence.mmd`

## Описание

Диаграмма Pipeline Execution Sequence показывает полный sequence flow выполнения pipeline от CLI invocation через bootstrap, data extraction, transformation, writes до cleanup на уровне System и использует нотацию sequenceDiagram. Материал помогает понять стандартный pipeline lifecycle и error handling paths в рамках сценария pipeline execution. В исходном файле прямо зафиксирован контекст: Complete sequence diagram showing pipeline execution flow from CLI invocation through bootstrap, data extraction, transformation, writes, and cleanup. Covers standard pipeline lifecycle and error handling paths. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые участники (participants) включают: CLI User, CLI Router, Bootstrap Service, Config Loader, Pipeline Service, Lock Service, Transformer, Storage Writer, Metrics/Tracing, Cleanup Service. Именно через эти участники визуализированы этапы выполнения pipeline и маршруты передачи сообщений. Примеры участников, отражающих доменную модель и инфраструктуру: Bootstrap Service (DI container registration), Pipeline Service (pipeline orchestration), Lock Service (lock acquisition/release), Transformer (extraction/transformation), Storage Writer (Silver/Gold writes), Metrics/Tracing (observability). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `sequence`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-010: Local-Only Deployment
- ADR-015: Pipeline Services Lifecycle
- ADR-018: Gold Strict Validation
- ADR-023: Entity Type Patterns
- ADR-032: Unified HTTP Client
- ADR-040: Diagram Governance

## Участники

### CLI User
- Инициатор pipeline execution
- Отправляет команду `bioetl run <pipeline> <config>`

### CLI Router
- Парсит CLI arguments
- Координирует загрузку конфигурации и инициализацию bootstrap

### Bootstrap Service
- Инициализирует DI container
- Регистрирует сервисы (ports, adapters)
- Инициализирует observability bundle

### Config Loader
- Загружает и валидирует pipeline config
- Проверяет YAML schema
- Предоставляет effective config artifact

### Pipeline Service
- Создаёт pipeline instance
- Управляет pipeline lifecycle
- Координирует lock acquisition, extraction, transformation, writes

### Lock Service
- Управляет lock acquisition/release
- Проверяет lock availability
- Предотвращает одновременное выполнение

### Transformer
- Выполняет extraction и transformation
- Применяет business logic, schema validation, DQ rules
- Генерирует metrics и spans

### Storage Writer
- Выполняет Silver и Gold writes
- Применяет DQ validation и strict validation (ADR-018)
- Управляет quarantine routing

### Metrics/Tracing
- Эмитирует metrics для всех этапов
- Управляет tracing spans
- Обеспечивает observability

### Cleanup Service
- Выполняет cleanup operations
- Закрывает connections
- Flushes metrics и закрывает tracer

## Sequence Flow

### CLI Invocation Phase
- CLI User → CLI Router: команда запуска
- CLI Router → Config Loader: загрузка конфигурации
- CLI Router → Bootstrap Service: инициализация DI контейнера

### Pipeline Instantiation Phase
- CLI Router → Pipeline Service: создание pipeline instance
- Pipeline Service → Config Loader: загрузка effective config
- Pipeline Service → Metrics/Tracing: инициализация observability

### Lock Acquisition Phase
- Pipeline Service → Lock Service: запрос lock
- Lock Service проверяет доступность lock
- Lock acquisition или lock denial

### Data Extraction Phase
- Pipeline Service → Transformer: инстанциация transformers
- Transformer → Config Loader: загрузка transformer configs
- Transformer выполняет extraction с metrics и spans

### Transformation Phase
- Pipeline Service → Transformer: применение transformations
- Transformer применяет schema validation и DQ rules
- Transformer генерирует metrics для transformation

### Silver Write Phase
- Pipeline Service → Storage Writer: запись Silver данных
- Storage Writer применяет DQ validation
- Commit to Silver или quarantine routing

### Gold Write Phase
- Pipeline Service → Storage Writer: запись Gold данных
- Storage Writer применяет strict validation (ADR-018)
- Commit to Gold или validation failure

### Error Handling Phase
- Обработка extraction, transformation, write errors
- Эмитация error metrics
- Запись ошибок в spans

### Cleanup and Shutdown Phase
- Pipeline Service → Lock Service: release lock
- Pipeline Service → Cleanup Service: cleanup operations
- Cleanup Service закрывает connections и flushes metrics
- Pipeline Service → CLI User: результат выполнения