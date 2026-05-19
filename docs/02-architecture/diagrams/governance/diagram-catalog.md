______________________________________________________________________

Version: 1.0.0
Status: 'historical planning artifact | Версия: 1.0 | Дата: 2026-01-20 | Актуализировано: 2026-03-19'
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Исторический Каталог Диаграмм BioETL

Этот документ сохраняется как historical/planning artifact и не является текущим canonical inventory.
Актуальный measured inventory и governance baseline ведутся через:

- `docs/02-architecture/diagrams/governance/diagrams-index.md`
- `docs/02-architecture/diagrams/governance/diagram-views-inventory.md`
- `docs/02-architecture/diagrams/governance/policy.md`

Содержимое ниже отражает раннюю catalog/program wave и может расходиться с текущим tracked set диаграмм.

______________________________________________________________________

## Категория 1: Архитектурные Обзоры (50 диаграмм)

### 1.1 Общая Архитектура (10)

1. **Hexagonal Architecture Overview** - C4 Context - Общий взгляд на Ports & Adapters архитектуру
1. **Five Layer Architecture** - Component - Слои: Domain, Application, Composition, Infrastructure, Interfaces
1. **Layer Dependency Matrix** - Matrix - Матрица разрешённых импортов между слоями
1. **Medallion Architecture Overview** - Flowchart - Bronze → Silver → Gold уровни
1. **DDD Strategic Design** - Context Map - Bounded contexts и их отношения
1. **System Context Diagram** - C4 Context - BioETL в контексте внешних систем
1. **Container Diagram** - C4 Container - Основные контейнеры системы
1. **Deployment Architecture** - Deployment - Local-only deployment модель
1. **Technology Stack** - Component - Все используемые технологии
1. **Architecture Decision Records Map** - Mind Map - 27 ADR и их связи

### 1.2 Domain Layer (10)

11. **Domain Model Overview** - Class - Все entities, value objects, aggregates
01. **Ports Architecture** - Interface - 24 порта и их категории
01. **DDD Aggregates** - Class - PipelineRun, Batch, QuarantineEntry с границами
01. **Domain Services** - Component - DefaultDataNormalizer, EntityIdentityGenerator и др.
01. **Value Objects Hierarchy** - Class - Все value objects и их отношения
01. **Entity Relationships** - ER - Связи между domain entities
01. **Configuration Objects** - Class - PipelineConfig, DQConfig, RuntimeConfig и др.
01. **Domain Events** - Sequence - Event sourcing для aggregates
01. **Invariants Enforcement** - Activity - Как aggregates поддерживают инварианты
01. **Domain Exceptions Hierarchy** - Class - BioETLError и подклассы

### 1.3 Application Layer (10)

21. **Pipeline Core Components** - Component - PipelineRunner, BatchExecutor, BatchProcessingService
01. **Pipeline Lifecycle** - State - Состояния выполнения пайплайна
01. **Services Architecture** - Component - 14 application services
01. **Transformer Hierarchy** - Class - BaseTransformer и конкретные реализации
01. **Pipeline Services Bundle** - Component - PipelineService и его компоненты
01. **Batch Processing Flow** - Activity - Полный цикл обработки батча
01. **Preflight Checklist** - Activity - PreflightService проверки
01. **Postrun Operations** - Activity - PostrunService cleanup
01. **Observability Integration** - Component - PipelineObserver интеграция
01. **Use Cases Overview** - Use Case - Основные use cases системы

### 1.4 Composition Layer (10)

31. **Composition Root** - Component - bootstrap-pipeline() orchestration
01. **Factory Pattern Usage** - Class - 8 фабрик и их ответственности
01. **Bootstrap Functions** - Flowchart - 10 bootstrap функций
01. **Dependency Injection Flow** - Sequence - Как собираются зависимости
01. **Pipeline Registry** - Component - Регистрация 30+ пайплайнов
01. **Provider Registration** - Component - 7 провайдеров
01. **Configuration Builders** - Class - FilterConfigBuilder и др.
01. **Entrypoints Mapping** - Flowchart - CLI → Composition → Application
01. **Services Factory** - Sequence - Создание PipelineService bundle
01. **Storage Factory** - Sequence - Создание storage adapters

### 1.5 Infrastructure Layer (10)

41. **Infrastructure Components** - Component - Все adapters и implementations
01. **Storage Architecture** - Component - Bronze/Silver/Gold writers
01. **HTTP Infrastructure** - Component - UnifiedHTTPClient и компоненты
01. **Provider Adapters Overview** - Component - 7 external API adapters + ID mapping provider seam
01. **Base Adapter Classes** - Class - BaseHttpAdapter, BaseSyncAdapter
01. **Checkpoint & Quarantine** - Component - State persistence
01. **Serialization Layer** - Component - JSON encoding/decoding
01. **Config Loader** - Flowchart - YAML → PipelineConfig
01. **Health Check Infrastructure** - Component - Health monitoring
01. **Metrics Collection** - Component - Prometheus metrics infrastructure

______________________________________________________________________

## Категория 2: Потоки Данных (60 диаграмм)

### 2.1 End-to-End Data Flow (10)

51. **Complete Pipeline Flow** - Flowchart - От API до Gold layer
01. **Bronze Layer Flow** - Sequence - Fetch → JSONL → Compress → Store
01. **Silver Layer Flow** - Sequence - Transform → Validate → Delta Merge
01. **Gold Layer Flow** - Sequence - Filter → Validate → Delta Write
01. **Incremental Run Flow** - Activity - Checkpoint → Fetch → Process → Write
01. **Backfill Run Flow** - Activity - Clear → Full Fetch → Process
01. **Rebuild Run Flow** - Activity - Exclusive Lock → Clear All → Rebuild
01. **Data Lineage** - Flowchart - Data provenance через слои
01. **Content Hash Calculation** - Activity - SHA256 hashing алгоритм
01. **Medallion Transformation** - Flowchart - Bronze → Silver → Gold трансформации

### 2.2 Provider-Specific Flows (14)

61. **ChEMBL Activity Pipeline** - Sequence - Полный flow для activity
01. **ChEMBL Molecule Pipeline** - Sequence - Molecule fetch → transform → write
01. **ChEMBL Target Pipeline** - Sequence - Target data processing
01. **PubChem Compound Pipeline** - Sequence - PubChem API → Storage
01. **UniProt Protein Pipeline** - Sequence - UniProt fetch → parse → store
01. **CrossRef Publication Pipeline** - Sequence - CrossRef API flow
01. **OpenAlex Work Pipeline** - Sequence - OpenAlex processing
01. **PubMed Article Pipeline** - Sequence - NCBI E-utilities flow
01. **SemanticScholar Pipeline** - Sequence - Semantic Scholar API
01. **ChEMBL Assay Pipeline** - Sequence - Assay data flow
01. **ChEMBL Compound Record Pipeline** - Sequence - Compound records
01. **UniProt ID Mapping** - Sequence - ID mapping transformation
01. **ChEMBL Cell Line Pipeline** - Sequence - Cell line data
01. **ChEMBL Protein Class Pipeline** - Sequence - Protein classification

### 2.3 Transformation Flows (12)

75. **BaseTransformer Template Method** - Activity - Template Method pattern
01. **Entity Mapping** - Activity - DTO → Domain Entity
01. **Data Normalization** - Activity - Text/Value/ID normalization
01. **Unit Conversion** - Activity - Unit converter flow
01. **Activity Aggregation** - Activity - Aggregating multiple activities
01. **Value Validation** - Activity - Molecular weight, activity validation
01. **SMILES Validation** - Activity - Chemical structure validation
01. **Taxonomy ID Resolution** - Activity - NCBI taxonomy lookup
01. **Date Normalization** - Activity - ISO date formatting
01. **PII Hashing** - Activity - Email/identifier hashing
01. **JSON Flattening** - Activity - Nested JSON → Flat schema
01. **Gold Filtering** - Activity - JSON field exclusion

### 2.4 Storage Operations (12)

87. **Bronze Write Operation** - Sequence - JSONL append with metadata
01. **Silver Merge Operation** - Sequence - Delta merge by content-hash
01. **Gold SCD2 Write** - Sequence - Slowly Changing Dimension Type 2
01. **Delta VACUUM** - Activity - Retention и cleanup
01. **Checkpoint Save** - Sequence - State persistence
01. **Checkpoint Load** - Sequence - Resume from checkpoint
01. **Quarantine Write** - Sequence - Failed record isolation
01. **Metadata Write** - Sequence - -metadata.yaml creation
01. **Bronze Archive** - Activity - 90d → Archive flow
01. **Silver Upsert** - Sequence - Insert or Update logic
01. **Gold Overwrite** - Sequence - Full table replacement
01. **Delta Read** - Sequence - Query Delta table

### 2.5 Batch Processing (12)

99. **Batch Creation** - State - Batch lifecycle states
01. **Record Addition** - Activity - add-record() flow
01. **Batch Sealing** - Activity - seal() operation
01. **Batch Writing** - Sequence - Mark writing → Commit
01. **Batch Failure** - Activity - mark-failed() и rollback
01. **Batch Metrics Recording** - Activity - BatchMetricsRecorderService
01. **Adaptive Batch Sizing** - Activity - Memory-based sizing
01. **Batch Transformation** - Sequence - BatchTransformer процесс
01. **Quarantine Handling** - Activity - Failed record flow
01. **Batch Validation** - Activity - Pre-write validation
01. **Batch Commit** - Activity - ACID commit операция
01. **Batch Rollback** - Activity - Failure recovery

______________________________________________________________________

## Категория 3: Паттерны и Механизмы (80 диаграмм)

### 3.1 Design Patterns (15)

111. **Ports & Adapters Pattern** - Component - Hexagonal architecture
001. **Repository Pattern** - Class - Data access abstraction
001. **Factory Pattern** - Class - Object creation
001. **Template Method Pattern** - Class - BaseTransformer
001. **Strategy Pattern** - Class - Write modes, clear policies
001. **Observer Pattern** - Sequence - PipelineObserver
001. **Null Object Pattern** - Class - NoOp implementations
001. **Dependency Injection** - Sequence - Constructor injection
001. **Aggregate Pattern** - Class - DDD aggregates
001. **Value Object Pattern** - Class - Immutable value objects
001. **Service Layer Pattern** - Component - Domain vs Application services
001. **Facade Pattern** - Class - Domain ports facade
001. **Builder Pattern** - Class - Configuration builders
001. **Adapter Pattern** - Class - Provider adapters
001. **Composite Pattern** - Class - Composite pipeline

### 3.2 Error Handling (15)

126. **Error Classification** - Flowchart - Critical/Recoverable/DQ
001. **Retry Mechanism** - Activity - Exponential backoff
001. **Circuit Breaker States** - State - Closed → Open → Half-Open
001. **Circuit Breaker Flow** - Sequence - Error detection → Trip
001. **Error Recovery** - Activity - Retry → Fallback → Fail
001. **Exception Hierarchy** - Class - BioETLError tree
001. **Error Propagation** - Sequence - Layer error handling
001. **DQ Error Handling** - Activity - Soft/Hard threshold
001. **Schema Violation Handling** - Activity - Gold strict validation
001. **Merge Conflict Resolution** - Activity - Silver merge conflicts
001. **Rate Limit Handling** - Sequence - 429 → Backoff → Retry
001. **Timeout Handling** - Activity - Request timeout recovery
001. **Auth Error Handling** - Activity - 401/403 critical errors
001. **Network Error Recovery** - Activity - Connection failures
001. **Graceful Degradation** - Flowchart - Fallback strategies

### 3.3 Observability (15)

141. **Tracing Architecture** - Component - OpenTelemetry integration
001. **Span Hierarchy** - Tree - Parent-child span relationships
001. **Metrics Collection** - Component - Prometheus metrics
001. **Logging Architecture** - Component - Structured logging
001. **DQ Monitoring** - Sequence - DQMonitorPort flow
001. **Health Checks** - Sequence - Component health probes
001. **Pipeline Observer Pattern** - Sequence - Cross-cutting concerns
001. **Metrics Emission** - Activity - Metric recording flow
001. **Log Correlation** - Flowchart - run-id correlation
001. **Trace Context Propagation** - Sequence - Distributed tracing
001. **Alerting Flow** - Flowchart - Metrics → Alerts
001. **Dashboard Data Flow** - Flowchart - Metrics → Dashboards
001. **Audit Trail** - Sequence - AuditPort recording
001. **Performance Monitoring** - Component - Latency tracking
001. **Error Rate Monitoring** - Component - Error metrics

### 3.4 Concurrency & Locking (15)

156. **Lock Acquisition Flow** - Sequence - acquire() → heartbeat → release()
001. **Lock States** - State - Unlocked → Locked → Released
001. **Heartbeat Mechanism** - Sequence - Periodic TTL refresh
001. **Lock Runtime Service** - Component - LockRuntimeService orchestration
001. **MemoryLock Implementation** - Class - In-memory locking
001. **Exclusive Lock Flow** - Sequence - Rebuild/backfill locking
001. **Lock Validation** - Activity - Owner validation
001. **Lock TTL Expiration** - Sequence - Auto-release
001. **Concurrent Pipeline Runs** - Sequence - Multiple runs
001. **Lock Contention** - Activity - Wait timeout handling
001. **Graceful Shutdown** - Sequence - SIGTERM → Cleanup → Exit
001. **Shutdown Signal Handling** - Activity - Signal propagation
001. **In-Flight Batch Completion** - Activity - Current batch finish
001. **Checkpoint on Shutdown** - Sequence - Save state before exit
001. **Resource Cleanup** - Activity - aclose() calls

### 3.5 Resilience & Reliability (20)

171. **Rate Limiting** - Activity - Token bucket algorithm
001. **Rate Limiter States** - State - Tokens available/exhausted
001. **Circuit Breaker Logic** - Flowchart - Failure threshold detection
001. **Circuit Breaker Recovery** - Sequence - Half-open probing
001. **Retry Policy** - Flowchart - Max attempts, backoff
001. **Exponential Backoff** - Activity - 2^n backoff calculation
001. **Jitter Addition** - Activity - Random jitter 0.1-0.5s
001. **Health Monitoring** - Sequence - Periodic health checks
001. **Provider Health Check** - Activity - Specific provider probe
001. **Fallback Strategies** - Flowchart - Primary → Fallback
001. **Idempotency** - Activity - Content hash deduplication
001. **ACID Guarantees** - Activity - Delta Lake transactions
001. **Checkpoint Recovery** - Sequence - Resume from last checkpoint
001. **Quarantine Isolation** - Activity - Failed record quarantine
001. **Data Integrity** - Activity - Schema validation
001. **Forensic Retention** - Activity - 7d Delta history
001. **VACUUM Safety** - Activity - Retention period enforcement
001. **Lock Safety** - Activity - Lock-before-write validation
001. **Memory Safety** - Activity - Adaptive batch sizing
001. **Timeout Protection** - Activity - Request timeout enforcement

______________________________________________________________________

## Категория 4: Компонентные Диаграммы (100 диаграмм)

### 4.1 Domain Components (20)

191. **PipelineRun Aggregate** - Class - Полная структура
001. **Batch Aggregate** - Class - Полная структура
001. **QuarantineEntry Aggregate** - Class - Полная структура
001. **StageResult VO** - Class - Immutable result object
001. **BatchRecord VO** - Class - Record representation
001. **Activity VO** - Class - Activity measurement
001. **DQMetrics VO** - Class - Quality metrics
001. **RunContext VO** - Class - Execution context
001. **CompoundIds VO** - Class - Compound identifiers
001. **TaxonomyId VO** - Class - Taxonomy ID handling
001. **Storage Port Family Interfaces** - Interface - Bronze/Silver/Gold/Merged storage contracts
001. **DataSourcePort Interface** - Interface - Data fetch contract
001. **LockPort Interface** - Interface - Locking contract
001. **CheckpointPort Interface** - Interface - State persistence
001. **QuarantinePort Interface** - Interface - Quarantine contract
001. **TracingPort Interface** - Interface - Tracing contract
001. **MetricsPort Interface** - Interface - Metrics contract
001. **LoggerPort Interface** - Interface - Logging contract
001. **ValidationConfig** - Class - Validation rules
001. **DQConfig** - Class - DQ configuration

### 4.2 Application Components (20)

211. **PipelineRunner** - Class - Runner structure
001. **BatchExecutor** - Class - Execution loop
001. **RecordProcessor** - Class - Record processing
001. **BatchTransformer** - Class - Transformation logic
001. **BatchWriter** - Class - Write orchestration
001. **BatchMetricsRecorderService** - Class - Metrics recording
001. **BaseTransformer** - Class - Abstract transformer
001. **BasePipeline** - Class - Abstract pipeline
001. **LockRuntimeService** - Class - Lock orchestration
001. **CheckpointRuntimeService** - Class - Checkpoint handling
001. **PipelineService** - Class - Services bundle
001. **QuarantineRuntimeService** - Class - Quarantine management
001. **PreflightService** - Class - Pre-run checks
001. **PostrunService** - Class - Post-run operations
001. **MemoryMonitor** - Class - Memory tracking
001. **Heartbeat** - Class - Lock heartbeat
001. **Shutdown** - Class - Shutdown coordination
001. **MedallionLifecycleService** - Class - Layer lifecycle
001. **DQReportService** - Class - DQ reporting
001. **PipelineObserver** - Class - Observability wrapper

### 4.3 Composition Components (15)

231. **bootstrap-pipeline()** - Sequence - Composition root
001. **bootstrap-observability()** - Sequence - Observability setup
001. **bootstrap-storage()** - Sequence - Storage setup
001. **PipelineFactory** - Class - Pipeline creation
001. **RunnerFactory** - Class - Runner creation
001. **ServicesFactory** - Class - Services creation
001. **StorageFactory** - Class - Storage creation
001. **HTTPClientFactory** - Class - HTTP client creation
001. **DataSourceFactory** - Class - Data source creation
001. **TransformerFactory** - Class - Transformer creation
001. **DQFactory** - Class - DQ analyzer creation
001. **PipelineRegistry** - Class - Registry implementation
001. **FilterConfigBuilder** - Class - Filter building
001. **ConfigurationLoader** - Class - YAML loading
001. **ProviderRegistration** - Sequence - 8 provider registrations, including `uniprot_idmapping`

### 4.4 Infrastructure Components (25)

246. **BronzeWriter** - Class - JSONL writer
001. **SilverWriter** - Class - Delta merge writer
001. **GoldWriter** - Class - Validated Delta writer
001. **BaseDeltaWriter** - Class - Common Delta operations
001. **DeltaReader** - Class - Delta table reader
001. **MetadataWriter** - Class - Metadata YAML writer
001. **RetentionPolicy** - Class - VACUUM and retention policy manager
001. **UnifiedHTTPClient** - Class - HTTP client
001. **RateLimiter** - Class - Rate limiting
001. **CircuitBreaker** - Class - Circuit breaker
001. **HealthMonitor** - Class - Health checking
001. **Pagination** - Class - Paginated requests
001. **ChemblAdapter** - Class - ChEMBL implementation
001. **PubChemAdapter** - Class - PubChem implementation
001. **UniProtAdapter** - Class - UniProt implementation
001. **CrossRefAdapter** - Class - CrossRef implementation
001. **OpenAlexAdapter** - Class - OpenAlex implementation
001. **PubMedAdapter** - Class - PubMed implementation
001. **SemanticScholarAdapter** - Class - SemanticScholar implementation
001. **BaseHttpAdapter** - Class - Base HTTP adapter
001. **BaseSyncAdapter** - Class - Sync-to-async wrapper
001. **CheckpointAdapter** - Class - Checkpoint storage
001. **QuarantineAdapter** - Class - Quarantine storage
001. **JsonEncoder** - Class - JSON serialization
001. **ConfigLoader** - Class - YAML configuration

### 4.5 Interface Components (20)

271. **CLI Main** - Component - Click CLI structure
001. **Run Command** - Sequence - Single pipeline execution
001. **RunAll Command** - Sequence - Multi-pipeline execution
001. **RunComposite Command** - Sequence - Composite execution
001. **Export Command** - Sequence - Data export
001. **Quarantine Command** - Sequence - Quarantine query
001. **Checkpoint Command** - Sequence - Checkpoint ops
001. **Lock Command** - Sequence - Lock management
001. **Health Command** - Sequence - Health checks
001. **Config Command** - Sequence - Config validation
001. **Maintenance Command** - Sequence - VACUUM/cleanup
001. **Formatters** - Class - Output formatting
001. **ExitCodes** - Class - Exit code definitions
001. **CLI Flow** - Flowchart - User input → execution
001. **Command Routing** - Flowchart - Command dispatch
001. **Error Display** - Activity - User-friendly errors
001. **Progress Display** - Activity - Progress bars
001. **Dry-Run Mode** - Activity - Preview operations
001. **Confirmation Prompts** - Activity - User confirmations
001. **Output Formatting** - Activity - Table/JSON output

______________________________________________________________________

## Категория 5: Взаимодействия (80 диаграмм)

### 5.1 Layer Interactions (15)

291. **Domain ↔ Application** - Sequence - Port usage
001. **Application ↔ Composition** - Sequence - Factory creation
001. **Composition ↔ Infrastructure** - Sequence - Adapter wiring
001. **Infrastructure ↔ External** - Sequence - API calls
001. **Interfaces → Composition** - Sequence - CLI → Bootstrap
001. **Cross-Layer Communication** - Sequence - Full stack call
001. **Port Implementation** - Sequence - Port → Adapter
001. **Dependency Flow** - Flowchart - Constructor injection chain
001. **Event Propagation** - Sequence - Domain events → Handlers
001. **Error Propagation** - Sequence - Exception bubbling
001. **Configuration Flow** - Sequence - YAML → Config objects
001. **Observability Flow** - Sequence - Tracing/metrics/logging
001. **Data Flow Across Layers** - Sequence - DTO → Entity → VO
001. **Service Coordination** - Sequence - Multiple services interaction
001. **Resource Cleanup** - Sequence - aclose() cascade

### 5.2 Component Interactions (20)

306. **Runner ↔ Executor** - Sequence - Pipeline execution
001. **Executor ↔ Processor** - Sequence - Batch processing
001. **Processor ↔ Transformer** - Sequence - Transformation
001. **Processor ↔ Writer** - Sequence - Storage write
001. **Writer ↔ Storage** - Sequence - Delta operations
001. **Adapter ↔ HTTPClient** - Sequence - API request
001. **HTTPClient ↔ RateLimiter** - Sequence - Rate limiting
001. **HTTPClient ↔ CircuitBreaker** - Sequence - Fault tolerance
001. **LockRuntimeService ↔ LockPort** - Sequence - Lock lifecycle
001. **CheckpointRuntimeService ↔ CheckpointPort** - Sequence - State persistence
001. **QuarantineRuntimeService ↔ QuarantinePort** - Sequence - Quarantine ops
001. **Observer ↔ Services** - Sequence - Observability integration
001. **Preflight ↔ HealthChecks** - Sequence - Pre-run validation
001. **Postrun ↔ DQAnalyzers** - Sequence - DQ analysis
001. **Postrun ↔ VacuumService** - Sequence - Cleanup
001. **MemoryMonitor ↔ BatchExecutor** - Sequence - Adaptive sizing
001. **Heartbeat ↔ LockRuntimeService** - Sequence - TTL refresh
001. **Shutdown ↔ Runner** - Sequence - Graceful stop
001. **Factory ↔ Registry** - Sequence - Component creation
001. **CLI ↔ Entrypoints** - Sequence - Command execution

### 5.3 Provider Interactions (14)

326. **ChEMBL API Integration** - Sequence - ChEMBL requests
001. **PubChem API Integration** - Sequence - PubChem requests
001. **UniProt API Integration** - Sequence - UniProt requests
001. **CrossRef API Integration** - Sequence - CrossRef requests
001. **OpenAlex API Integration** - Sequence - OpenAlex requests
001. **PubMed API Integration** - Sequence - NCBI E-utilities
001. **SemanticScholar API Integration** - Sequence - S2 API
001. **ChEMBL Entity Mapping** - Activity - DTO → Entity
001. **PubChem Response Parsing** - Activity - XML/JSON parsing
001. **UniProt FASTA Parsing** - Activity - FASTA format
001. **CrossRef Fallback** - Sequence - Primary → Fallback
001. **PubMed XML Processing** - Activity - XML parsing
001. **Rate Limit Coordination** - Sequence - Multi-provider limits
001. **Health Check Probes** - Sequence - All providers

### 5.4 Storage Interactions (16)

340. **Bronze Write Flow** - Sequence - File system operations
001. **Silver Merge Flow** - Sequence - Delta merge logic
001. **Gold Write Flow** - Sequence - Validated write
001. **Delta Transaction** - Sequence - ACID commit
001. **VACUUM Operation** - Sequence - Delta cleanup
001. **Checkpoint Save Flow** - Sequence - State write
001. **Checkpoint Load Flow** - Sequence - State read
001. **Quarantine Write Flow** - Sequence - Failed record save
001. **Metadata Write Flow** - Sequence - YAML sidecar
001. **Archive Operation** - Sequence - Bronze archival
001. **Content Hash Check** - Sequence - Deduplication
001. **Schema Validation** - Sequence - Pandera validation
001. **Gold Filtering** - Sequence - JSON exclusion
001. **SCD2 Implementation** - Sequence - Type 2 slowly changing
001. **Delta History Query** - Sequence - Time travel
001. **Forensic Retrieval** - Sequence - Historical data access

### 5.5 DQ & Validation (15)

356. **DQ Check Flow** - Sequence - Complete DQ process
001. **Soft Threshold Check** - Activity - 5% warning
001. **Hard Threshold Check** - Activity - 20% failure
001. **Bronze DQ Analysis** - Sequence - Bronze layer DQ
001. **Silver DQ Analysis** - Sequence - Silver layer DQ
001. **Gold DQ Analysis** - Sequence - Gold layer DQ
001. **DQ Report Generation** - Sequence - Report creation
001. **DQ Metrics Emission** - Sequence - Prometheus metrics
001. **Schema Violation Detection** - Activity - Schema mismatch
001. **Field Validation** - Activity - Single field rules
001. **Cross-Field Validation** - Activity - Multi-field rules
001. **Conditional Validation** - Activity - If-then rules
001. **SMILES Validation** - Activity - Chemical validation
001. **Molecular Weight Validation** - Activity - MW range check
001. **Activity Value Validation** - Activity - pChEMBL validation

______________________________________________________________________

## Категория 6: Состояния и Жизненные Циклы (40 диаграмм)

### 6.1 Aggregate Lifecycles (10)

371. **PipelineRun States** - State - PENDING → RUNNING → COMPLETED/FAILED
001. **PipelineRun Transitions** - State - All state transitions
001. **Batch States** - State - OPEN → SEALED → WRITING → COMMITTED
001. **Batch Lifecycle** - Sequence - Creation → Sealing → Commit
001. **QuarantineEntry States** - State - NEW → UNDER-REVIEW → RESOLVED
001. **QuarantineEntry Lifecycle** - Sequence - Creation → Resolution
001. **StageResult States** - State - SUCCESS/FAILED/SKIPPED
001. **Event Collection** - Sequence - collect-events() flow
001. **Aggregate Immutability** - Activity - State protection
001. **Aggregate Persistence** - Sequence - Event sourcing

### 6.2 Component Lifecycles (15)

381. **Pipeline Lifecycle** - State - Full pipeline states
001. **Lock Lifecycle** - State - Acquire → Heartbeat → Release
001. **Checkpoint Lifecycle** - State - Create → Update → Load
001. **Circuit Breaker Lifecycle** - State - Closed → Open → Half-Open
001. **HTTP Request Lifecycle** - Sequence - Request → Retry → Response
001. **Batch Processing Lifecycle** - Sequence - Create → Process → Write
001. **Record Processing Lifecycle** - Sequence - Fetch → Transform → Write
001. **Transformer Lifecycle** - Sequence - Setup → Transform → Teardown
001. **Writer Lifecycle** - Sequence - Open → Write → Close
001. **Adapter Lifecycle** - Sequence - Initialize → Use → Cleanup
001. **Service Lifecycle** - Sequence - Start → Run → Stop
001. **Observer Lifecycle** - Sequence - Setup → Observe → Report
001. **MemoryMonitor Lifecycle** - Sequence - Initialize → Monitor → Adjust
001. **Heartbeat Lifecycle** - Sequence - Start → Beat → Stop
001. **Shutdown Lifecycle** - Sequence - Signal → Cleanup → Exit

### 6.3 Session & Run Types (15)

396. **Incremental Run** - Flowchart - Resume from checkpoint
001. **Backfill Run** - Flowchart - Historical data load
001. **Rebuild Run** - Flowchart - Full rebuild
001. **Dry-Run Mode** - Flowchart - Preview without writes
001. **Run Type Decision** - Flowchart - Mode selection
001. **Session Initialization** - Sequence - Setup phase
001. **Session Execution** - Sequence - Main execution
001. **Session Termination** - Sequence - Cleanup phase
001. **Multi-Pipeline Session** - Sequence - RunAll execution
001. **Composite Pipeline Session** - Sequence - Composite execution
001. **Export Session** - Sequence - Data export flow
001. **Maintenance Session** - Sequence - VACUUM/cleanup
001. **Health Check Session** - Sequence - Health validation
001. **Quarantine Review Session** - Sequence - Quarantine inspection
001. **Config Validation Session** - Sequence - Config check

______________________________________________________________________

## Категория 7: Конфигурация и Схемы (30 диаграмм)

### 7.1 Configuration (15)

411. **PipelineConfig Structure** - Class - Complete configuration
001. **RuntimeConfig Structure** - Class - CLI parameters
001. **DQConfig Structure** - Class - DQ thresholds
001. **ValidationConfig Structure** - Class - Validation rules
001. **TableConfig Structure** - Class - Table names/keys
001. **Config Loading Flow** - Sequence - YAML → Objects
001. **Config Validation** - Activity - Config schema validation
001. **Config Overrides** - Flowchart - CLI → ENV → File priority
001. **FilterConfig Building** - Sequence - Filter construction
001. **Default Config** - Activity - Default values
001. **Provider-Specific Config** - Class - Per-provider settings
001. **Entity-Specific Config** - Class - Per-entity settings
001. **DQ Rules Configuration** - Tree - Hierarchical rules
001. **Medallion Policy Config** - Class - Clear/VACUUM policies
001. **Write Mode Config** - Class - Silver/Gold write modes

### 7.2 Schemas (15)

426. **Bronze Schema** - ER - JSONL structure
001. **Silver Schema** - ER - Delta table schema
001. **Gold Schema** - ER - Validated Delta schema
001. **ChEMBL Activity Schema** - Class - Pandera schema
001. **ChEMBL Molecule Schema** - Class - Pandera schema
001. **PubChem Compound Schema** - Class - Pandera schema
001. **UniProt Protein Schema** - Class - Pandera schema
001. **CrossRef Publication Schema** - Class - Pandera schema
001. **Metadata Schema** - Class - -metadata.yaml structure
001. **Checkpoint Schema** - Class - Checkpoint JSON structure
001. **Quarantine Schema** - Class - Quarantine entry schema
001. **DQ Report Schema** - Class - DQ report structure
001. **Audit Schema** - Class - Audit trail schema
001. **Schema Evolution** - Flowchart - Schema versioning
001. **Schema Validation Flow** - Sequence - Pandera validation

______________________________________________________________________

## Категория 8: Provider-Specific (70 диаграмм)

### 8.1 ChEMBL (15)

441. **ChEMBL Adapter Architecture** - Component - Full adapter
001. **ChEMBL Entity Mapper** - Class - Entity mapping
001. **ChEMBL Activity Flow** - Sequence - Activity pipeline
001. **ChEMBL Molecule Flow** - Sequence - Molecule pipeline
001. **ChEMBL Target Flow** - Sequence - Target pipeline
001. **ChEMBL Assay Flow** - Sequence - Assay pipeline
001. **ChEMBL DTO Models** - Class - All DTO classes
001. **ChEMBL Health Check** - Sequence - Status endpoint
001. **ChEMBL Pagination** - Sequence - Paginated fetch
001. **ChEMBL Error Handling** - Flowchart - Error classification
001. **ChEMBL Rate Limiting** - Activity - No rate limit
001. **ChEMBL Response Parsing** - Activity - JSON parsing
001. **ChEMBL Transform Logic** - Activity - Activity transform
001. **ChEMBL Compound Record** - Sequence - Compound flow
001. **ChEMBL Cell Line** - Sequence - Cell line flow

### 8.2 PubChem (10)

456. **PubChem Adapter Architecture** - Component - Full adapter
001. **PubChem Entity Mapper** - Class - Entity mapping
001. **PubChem Compound Flow** - Sequence - Compound pipeline
001. **PubChem Fetch Strategies** - Class - Multiple strategies
001. **PubChem Health Check** - Sequence - Lightweight query
001. **PubChem Rate Limiting** - Activity - 5 req/sec
001. **PubChem Response Parsing** - Activity - XML/JSON parsing
001. **PubChem Transform Logic** - Activity - Compound transform
001. **PubChem Error Handling** - Flowchart - Error classification
001. **PubChem Pagination** - Sequence - Batch fetching

### 8.3 UniProt (10)

466. **UniProt Adapter Architecture** - Component - Full adapter
001. **UniProt Entity Mapper** - Class - Entity mapping
001. **UniProt Protein Flow** - Sequence - Protein pipeline
001. **UniProt ID Mapping Flow** - Sequence - ID mapping
001. **UniProt FASTA Parsing** - Activity - FASTA format
001. **UniProt Health Check** - Sequence - Search probe
001. **UniProt Rate Limiting** - Activity - 100 req/sec
001. **UniProt Response Parsing** - Activity - TSV/FASTA parsing
001. **UniProt Transform Logic** - Activity - Protein transform
001. **UniProt Error Handling** - Flowchart - Error classification

### 8.4 CrossRef (10)

476. **CrossRef Adapter Architecture** - Component - Full adapter
001. **CrossRef Entity Mapper** - Class - Entity mapping
001. **CrossRef Publication Flow** - Sequence - Publication pipeline
001. **CrossRef Fallback Strategy** - Sequence - Primary → Fallback
001. **CrossRef Health Check** - Sequence - Works endpoint
001. **CrossRef Rate Limiting** - Activity - Polite pool
001. **CrossRef Response Parsing** - Activity - JSON parsing
001. **CrossRef Transform Logic** - Activity - Publication transform
001. **CrossRef Error Handling** - Flowchart - Error classification
001. **CrossRef Pagination** - Sequence - Cursor-based pagination

### 8.5 OpenAlex (5)

486. **OpenAlex Adapter Architecture** - Component - Full adapter
001. **OpenAlex Entity Mapper** - Class - Entity mapping
001. **OpenAlex Work Flow** - Sequence - Work pipeline
001. **OpenAlex Rate Limiting** - Activity - 10 req/sec
001. **OpenAlex Transform Logic** - Activity - Work transform

### 8.6 PubMed (10)

491. **PubMed Adapter Architecture** - Component - Full adapter
001. **PubMed Entity Mapper** - Class - Entity mapping
001. **PubMed Article Flow** - Sequence - Article pipeline
001. **PubMed XML Processing** - Activity - XML parsing
001. **PubMed E-utilities Flow** - Sequence - NCBI API
001. **PubMed Health Check** - Sequence - EInfo endpoint
001. **PubMed Rate Limiting** - Activity - 3 req/sec
001. **PubMed Response Parsing** - Activity - XML to entity
001. **PubMed Transform Logic** - Activity - Article transform
001. **PubMed Error Handling** - Flowchart - Error classification

______________________________________________________________________

## Приоритизация для Выбора TOP-50

Каждая диаграмма будет оценена по критериям:

1. **Архитектурная важность** (1-10): Насколько критична для понимания архитектуры
1. **Документационная ценность** (1-10): Полезность для новых разработчиков
1. **Частота использования** (1-10): Как часто нужна при работе с проектом
1. **Сложность без диаграммы** (1-10): Насколько сложно понять без визуализации
1. **Охват кодовой базы** (1-10): Сколько компонентов покрывает

**Формула приоритета**: `(Arch * 2 + Doc * 1.5 + Freq * 1.5 + Complex * 2 + Coverage * 1) / 8`

______________________________________________________________________

*Следующий шаг: Оценка и выбор TOP-50 диаграмм*
