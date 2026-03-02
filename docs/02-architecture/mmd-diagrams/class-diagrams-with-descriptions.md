# BioETL Class Diagrams with Descriptions

Сгенерировано: 2026-03-02T15:21:56.693371+03:00

## 01-domain-ports — 01 Domain Ports

![01-domain-ports](class-diagrams/png/01-domain-ports.png)

Диаграмма Domain Port Protocols показывает архитектурную модель модуля `01-domain-ports` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: All Protocol interfaces defined in domain/ports/. На схеме отражено примерно 19 классов и 1 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

<div style="page-break-after: always;"></div>

## 02-entities-aggregates — 02 Entities Aggregates

![02-entities-aggregates](class-diagrams/png/02-entities-aggregates.png)

Диаграмма Entities & Aggregates показывает архитектурную модель модуля `02-entities-aggregates` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain entities, aggregate roots, and their relationships. На схеме отражено примерно 13 классов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

<div style="page-break-after: always;"></div>

## 03-value-objects — 03 Value Objects

![03-value-objects](class-diagrams/png/03-value-objects.png)

Диаграмма Value Objects показывает архитектурную модель модуля `03-value-objects` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Immutable domain value objects. На схеме отражено примерно 17 классов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

<div style="page-break-after: always;"></div>

## 04-types-enums — 04 Types Enums

![04-types-enums](class-diagrams/png/04-types-enums.png)

Диаграмма Types & Enums показывает архитектурную модель модуля `04-types-enums` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: All type aliases, NewTypes, and enumerations. На схеме отражено примерно 19 классов и 0 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

<div style="page-break-after: always;"></div>

## 05-exceptions — 05 Exceptions

![05-exceptions](class-diagrams/png/05-exceptions.png)

Диаграмма Exception Hierarchy показывает архитектурную модель модуля `05-exceptions` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain exception tree. На схеме отражено примерно 19 классов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

<div style="page-break-after: always;"></div>

## 06-config-classes — 06 Config Classes

![06-config-classes](class-diagrams/png/06-config-classes.png)

Диаграмма Configuration Classes показывает архитектурную модель модуля `06-config-classes` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain and application configuration hierarchy. На схеме отражено примерно 14 классов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

<div style="page-break-after: always;"></div>

## 07-application-core-services — 07 Application Core Services

![07-application-core-services](class-diagrams/png/07-application-core-services.png)

Диаграмма Application Core Services показывает архитектурную модель модуля `07-application-core-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: PipelineRunner, BatchExecutor, and their composition. На схеме отражено примерно 16 классов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: PipelineRunner, PipelineServices, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManager.

<div style="page-break-after: always;"></div>

## 08-application-services — 08 Application Services

![08-application-services](class-diagrams/png/08-application-services.png)

Диаграмма Application Services показывает архитектурную модель модуля `08-application-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: High-level application services. На схеме отражено примерно 19 классов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

<div style="page-break-after: always;"></div>

## 09-transformers — 09 Transformers

![09-transformers](class-diagrams/png/09-transformers.png)

Диаграмма Transformers показывает архитектурную модель модуля `09-transformers` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: BaseTransformer hierarchy and provider-specific implementations. На схеме отражено примерно 20 классов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

<div style="page-break-after: always;"></div>

## 10-adapters — 10 Adapters

![10-adapters](class-diagrams/png/10-adapters.png)

Диаграмма Infrastructure Adapters показывает архитектурную модель модуля `10-adapters` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: HTTP adapter class hierarchy with mixins. На схеме отражено примерно 18 классов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

<div style="page-break-after: always;"></div>

## 11-storage — 11 Storage

![11-storage](class-diagrams/png/11-storage.png)

Диаграмма Storage Components показывает архитектурную модель модуля `11-storage` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Bronze/Silver/Gold writers and supporting classes. На схеме отражено примерно 16 классов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

<div style="page-break-after: always;"></div>

## 12-composite-pipeline — 12 Composite Pipeline

![12-composite-pipeline](class-diagrams/png/12-composite-pipeline.png)

Диаграмма Composite Pipeline Components показывает архитектурную модель модуля `12-composite-pipeline` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Runner, coordinators, merge service, and FSM. На схеме отражено примерно 14 классов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

<div style="page-break-after: always;"></div>

## 13-domain-services — 13 Domain Services

![13-domain-services](class-diagrams/png/13-domain-services.png)

Диаграмма Domain Services показывает архитектурную модель модуля `13-domain-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Pure domain services without I/O. На схеме отражено примерно 10 классов и 0 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

<div style="page-break-after: always;"></div>

## 14-observability — 14 Observability

![14-observability](class-diagrams/png/14-observability.png)

Диаграмма Observability Components показывает архитектурную модель модуля `14-observability` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Logging, metrics, tracing implementations. На схеме отражено примерно 19 классов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

<div style="page-break-after: always;"></div>

## 15-extractors — 15 Extractors

![15-extractors](class-diagrams/png/15-extractors.png)

Диаграмма Field Extractors показывает архитектурную модель модуля `15-extractors` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Extractor pattern used in transformers. На схеме отражено примерно 12 классов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

<div style="page-break-after: always;"></div>

## 16-factories-bootstrap — 16 Factories Bootstrap

![16-factories-bootstrap](class-diagrams/png/16-factories-bootstrap.png)

Диаграмма Factories & Bootstrap показывает архитектурную модель модуля `16-factories-bootstrap` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Composition layer factories and DI assembly. На схеме отражено примерно 13 классов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataSourceRegistry, TransformerFactory, RunnerFactory, DQFactory, RuntimeAssembly, RunnerBootstrap.

