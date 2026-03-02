# BioETL Class Diagrams with Descriptions

Сгенерировано: 2026-03-02T16:16:38+03:00

## 01-domain-ports — Domain Port Protocols

![01-domain-ports](class-diagrams/png/01-domain-ports.png)

Диаграмма «Domain Port Protocols» описывает модуль `01-domain-ports` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: All Protocol interfaces defined in domain/ports/ В текущей версии выделено примерно 19 классов и 1 связей. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

\newpage

## 01a-domain-ports-method-catalog — Domain Port Method Catalog (L2)

![01a-domain-ports-method-catalog](class-diagrams/png/01a-domain-ports-method-catalog.png)

Диаграмма «Domain Port Method Catalog (L2)» описывает модуль `01a-domain-ports-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 01-domain-ports L1 overview. В текущей версии выделено примерно 13 классов и 1 связей. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

\newpage

## 02-entities-aggregates — Entities & Aggregates

![02-entities-aggregates](class-diagrams/png/02-entities-aggregates.png)

Диаграмма «Entities & Aggregates» описывает модуль `02-entities-aggregates` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain entities, aggregate roots, and their relationships. В текущей версии выделено примерно 13 классов и 9 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

\newpage

## 03-value-objects — Value Objects

![03-value-objects](class-diagrams/png/03-value-objects.png)

Диаграмма «Value Objects» описывает модуль `03-value-objects` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Immutable domain value objects. В текущей версии выделено примерно 17 классов и 6 связей. Для быстрого чтения и ревью полезно начать с элементов: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

\newpage

## 04-types-enums — Types & Enums

![04-types-enums](class-diagrams/png/04-types-enums.png)

Диаграмма «Types & Enums» описывает модуль `04-types-enums` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: All type aliases, NewTypes, and enumerations. В текущей версии выделено примерно 19 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

\newpage

## 05-exceptions — Exception Hierarchy

![05-exceptions](class-diagrams/png/05-exceptions.png)

Диаграмма «Exception Hierarchy» описывает модуль `05-exceptions` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain exception tree. В текущей версии выделено примерно 19 классов и 18 связей. Для быстрого чтения и ревью полезно начать с элементов: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

\newpage

## 06-config-classes — Configuration Classes

![06-config-classes](class-diagrams/png/06-config-classes.png)

Диаграмма «Configuration Classes» описывает модуль `06-config-classes` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain and application configuration hierarchy. В текущей версии выделено примерно 14 классов и 10 связей. Для быстрого чтения и ревью полезно начать с элементов: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

\newpage

## 07-application-core-services — Application Core Services

![07-application-core-services](class-diagrams/png/07-application-core-services.png)

Диаграмма «Application Core Services» описывает модуль `07-application-core-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: PipelineRunner, BatchExecutor, and their composition. В текущей версии выделено примерно 16 классов и 17 связей. Для быстрого чтения и ревью полезно начать с элементов: PipelineRunner, PipelineServices, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManager.

\newpage

## 08-application-services — Application Services

![08-application-services](class-diagrams/png/08-application-services.png)

Диаграмма «Application Services» описывает модуль `08-application-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: High-level application services. В текущей версии выделено примерно 19 классов и 4 связей. Для быстрого чтения и ревью полезно начать с элементов: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

\newpage

## 08a-application-services-operation-catalog — Application Service Operation Catalog (L2)

![08a-application-services-operation-catalog](class-diagrams/png/08a-application-services-operation-catalog.png)

Диаграмма «Application Service Operation Catalog (L2)» описывает модуль `08a-application-services-operation-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed operational methods extracted from 08-application-services L1 overview. В текущей версии выделено примерно 9 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: MedallionLifecycleService, VacuumService, PipelineObserver, CheckpointService, MetricsService, QuarantineService.

\newpage

## 09-transformers — Transformers

![09-transformers](class-diagrams/png/09-transformers.png)

Диаграмма «Transformers» описывает модуль `09-transformers` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: BaseTransformer hierarchy and provider-specific implementations. В текущей версии выделено примерно 20 классов и 19 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

\newpage

## 10-adapters — Infrastructure Adapters

![10-adapters](class-diagrams/png/10-adapters.png)

Диаграмма «Infrastructure Adapters» описывает модуль `10-adapters` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: HTTP adapter class hierarchy with mixins. В текущей версии выделено примерно 18 классов и 14 связей. Для быстрого чтения и ревью полезно начать с элементов: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

\newpage

## 11-storage — Storage Components

![11-storage](class-diagrams/png/11-storage.png)

Диаграмма «Storage Components» описывает модуль `11-storage` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Bronze/Silver/Gold writers and supporting classes. В текущей версии выделено примерно 16 классов и 17 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

\newpage

## 12-composite-pipeline — Composite Pipeline Components

![12-composite-pipeline](class-diagrams/png/12-composite-pipeline.png)

Диаграмма «Composite Pipeline Components» описывает модуль `12-composite-pipeline` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Runner, coordinators, merge service, and FSM. В текущей версии выделено примерно 14 классов и 13 связей. Для быстрого чтения и ревью полезно начать с элементов: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

\newpage

## 13-domain-services — Domain Services

![13-domain-services](class-diagrams/png/13-domain-services.png)

Диаграмма «Domain Services» описывает модуль `13-domain-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Pure domain services without I/O. В текущей версии выделено примерно 10 классов и 0 связей. Для быстрого чтения и ревью полезно начать с элементов: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

\newpage

## 14-observability — Observability Components

![14-observability](class-diagrams/png/14-observability.png)

Диаграмма «Observability Components» описывает модуль `14-observability` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Logging, metrics, tracing implementations. В текущей версии выделено примерно 19 классов и 14 связей. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

\newpage

## 14a-observability-method-catalog — Observability Method Catalog (L2)

![14a-observability-method-catalog](class-diagrams/png/14a-observability-method-catalog.png)

Диаграмма «Observability Method Catalog (L2)» описывает модуль `14a-observability-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 14-observability L1 overview. В текущей версии выделено примерно 9 классов и 5 связей. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, MetricsPort, MetricsCollector, PrometheusMetrics, MetricsServerAdapter.

\newpage

## 15-extractors — Field Extractors

![15-extractors](class-diagrams/png/15-extractors.png)

Диаграмма «Field Extractors» описывает модуль `15-extractors` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Extractor pattern used in transformers. В текущей версии выделено примерно 12 классов и 11 связей. Для быстрого чтения и ревью полезно начать с элементов: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

\newpage

## 16-factories-bootstrap — Factories & Bootstrap

![16-factories-bootstrap](class-diagrams/png/16-factories-bootstrap.png)

Диаграмма «Factories & Bootstrap» описывает модуль `16-factories-bootstrap` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Composition layer factories and DI assembly. В текущей версии выделено примерно 13 классов и 12 связей. Для быстрого чтения и ревью полезно начать с элементов: DataSourceRegistry, TransformerFactory, RunnerFactory, DQFactory, RuntimeAssembly, RunnerBootstrap.

