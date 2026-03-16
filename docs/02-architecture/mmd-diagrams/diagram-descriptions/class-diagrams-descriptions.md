# Class Diagram Descriptions

Сгенерировано: 2026-03-02T16:37:55+03:00

## 01-domain-ports — Domain Port Protocols

Диаграмма «Domain Port Protocols» описывает модуль `01-domain-ports` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: all protocol interfaces defined in `domain/ports`, включая narrow storage ports и backward-compatible aggregate `StoragePort`. В текущей версии выделено примерно 19 классов и 1 связей. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

## 01a-domain-ports-method-catalog — Domain Port Method Catalog (L2)

Диаграмма «Domain Port Method Catalog (L2)» описывает модуль `01a-domain-ports-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 01-domain-ports L1 overview. В текущей версии выделено примерно 13 классов и 1 связей. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

## 02-entities-aggregates — Entities & Aggregates

Диаграмма «Entities & Aggregates» описывает модуль `02-entities-aggregates` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain entities, aggregate roots, and their relationships. В текущей версии выделено примерно 13 классов и 9 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

## 03-value-objects — Value Objects

Диаграмма «Value Objects» описывает модуль `03-value-objects` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Immutable domain value objects. В текущей версии выделено примерно 17 классов и 6 связей. Для быстрого чтения и ревью полезно начать с элементов: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

## 04-types-enums — Types & Enums

Диаграмма «Types & Enums» описывает модуль `04-types-enums` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: All type aliases, NewTypes, and enumerations. В текущей версии выделено примерно 19 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

## 05-exceptions — Exception Hierarchy

Диаграмма «Exception Hierarchy» описывает модуль `05-exceptions` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain exception tree. В текущей версии выделено примерно 19 классов и 18 связей. Для быстрого чтения и ревью полезно начать с элементов: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

## 06-config-classes — Configuration Classes

Диаграмма «Configuration Classes» описывает модуль `06-config-classes` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain and application configuration hierarchy. В текущей версии выделено примерно 14 классов и 10 связей. Для быстрого чтения и ревью полезно начать с элементов: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

## 07-application-core-services — Application Core Services

Диаграмма «Application Core Services» описывает модуль `07-application-core-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: PipelineRunner, BatchExecutor, and their composition. В текущей версии выделено примерно 16 классов и 17 связей. Для быстрого чтения и ревью полезно начать с элементов: PipelineRunner, PipelineServices, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManager.

## 08-application-services — Application Services

Диаграмма «Application Services» описывает модуль `08-application-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: High-level application services. В текущей версии выделено примерно 19 классов и 4 связей. Для быстрого чтения и ревью полезно начать с элементов: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

## 08a-application-services-operation-catalog — Application Service Operation Catalog (L2)

Диаграмма «Application Service Operation Catalog (L2)» описывает модуль `08a-application-services-operation-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed operational methods extracted from 08-application-services L1 overview. В текущей версии выделено примерно 9 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: MedallionLifecycleService, VacuumService, PipelineObserver, CheckpointService, MetricsService, QuarantineService.

## 09-transformers — Transformers

Диаграмма «Transformers» описывает модуль `09-transformers` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: BaseTransformer hierarchy and provider-specific implementations. В текущей версии выделено примерно 20 классов и 19 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

## 10-adapters — Infrastructure Adapters

Диаграмма «Infrastructure Adapters» описывает модуль `10-adapters` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: HTTP adapter class hierarchy with mixins. В текущей версии выделено примерно 18 классов и 14 связей. Для быстрого чтения и ревью полезно начать с элементов: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

## 11-storage — Storage Components

Диаграмма «Storage Components» описывает модуль `11-storage` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Bronze/Silver/Gold writers and supporting classes. В текущей версии выделено примерно 16 классов и 17 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

## 12-composite-pipeline — Composite Pipeline Components

Диаграмма «Composite Pipeline Components» описывает модуль `12-composite-pipeline` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Runner, coordinators, merge service, and FSM. В текущей версии выделено примерно 14 классов и 13 связей. Для быстрого чтения и ревью полезно начать с элементов: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

## 13-domain-services — Domain Services

Диаграмма «Domain Services» описывает модуль `13-domain-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Pure domain services without I/O. В текущей версии выделено примерно 10 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

## 14-observability — Observability Components

Диаграмма «Observability Components» описывает модуль `14-observability` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Logging, metrics, tracing implementations. В текущей версии выделено примерно 19 классов и 14 связей. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

## 14a-observability-method-catalog — Observability Method Catalog (L2)

Диаграмма «Observability Method Catalog (L2)» описывает модуль `14a-observability-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 14-observability L1 overview. В текущей версии выделено примерно 9 классов и 5 связей. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, MetricsPort, MetricsCollector, PrometheusMetrics, MetricsServerAdapter.

## 15-extractors — Field Extractors

Диаграмма «Field Extractors» описывает модуль `15-extractors` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Extractor pattern used in transformers. В текущей версии выделено примерно 12 классов и 11 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

## 16-factories-bootstrap — Factories & Bootstrap

Диаграмма «Factories & Bootstrap» описывает модуль `16-factories-bootstrap` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: current composition-layer factories, provider registry, and runtime assembly seams. В текущей версии выделено примерно 9 классов и 7 связей. Для быстрого чтения и ревью полезно начать с элементов: ProviderRegistry, DataSourceFactory, PipelineRegistry, RunnerFactory, RunnerFactoryBuilderService, CompositeSupportServicesFactory.
