# BioETL Class Diagrams with Descriptions

Сгенерировано: 2026-03-03T09:44:02+03:00

Всего диаграмм: 19

\newpage

<div style="page-break-before: always;"></div>

## 01-domain-ports — Domain Port Protocols

![01-domain-ports](class-diagrams/png/01-domain-ports.png)

### Описание
Диаграмма Domain Port Protocols показывает архитектурную модель модуля `01-domain-ports` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: All Protocol interfaces defined in domain/ports/. На схеме отражено примерно 19 классов и 1 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

\newpage

<div style="page-break-before: always;"></div>

## 01a-domain-ports-method-catalog — Domain Port Method Catalog (L2)

![01a-domain-ports-method-catalog](class-diagrams/png/01a-domain-ports-method-catalog.png)

### Описание
Диаграмма «Domain Port Method Catalog (L2)» описывает модуль `01a-domain-ports-method-catalog` и фиксирует ключевые классы, контракты и связи на уровне `Class / Interface`. Основной фокус: Detailed method surface extracted from 01-domain-ports L1 overview.

\newpage

<div style="page-break-before: always;"></div>

## 02-entities-aggregates — Entities & Aggregates

![02-entities-aggregates](class-diagrams/png/02-entities-aggregates.png)

### Описание
Диаграмма Entities & Aggregates показывает архитектурную модель модуля `02-entities-aggregates` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain entities, aggregate roots, and their relationships. На схеме отражено примерно 13 классов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

\newpage

<div style="page-break-before: always;"></div>

## 03-value-objects — Value Objects

![03-value-objects](class-diagrams/png/03-value-objects.png)

### Описание
Диаграмма Value Objects показывает архитектурную модель модуля `03-value-objects` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Immutable domain value objects. На схеме отражено примерно 17 классов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

\newpage

<div style="page-break-before: always;"></div>

## 04-types-enums — Types & Enums

![04-types-enums](class-diagrams/png/04-types-enums.png)

### Описание
Диаграмма Types & Enums показывает архитектурную модель модуля `04-types-enums` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: All type aliases, NewTypes, and enumerations. На схеме отражено примерно 19 классов и 0 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

\newpage

<div style="page-break-before: always;"></div>

## 05-exceptions — Exception Hierarchy

![05-exceptions](class-diagrams/png/05-exceptions.png)

### Описание
Диаграмма Exception Hierarchy показывает архитектурную модель модуля `05-exceptions` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain exception tree. На схеме отражено примерно 19 классов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

\newpage

<div style="page-break-before: always;"></div>

## 06-config-classes — Configuration Classes

![06-config-classes](class-diagrams/png/06-config-classes.png)

### Описание
Диаграмма Configuration Classes показывает архитектурную модель модуля `06-config-classes` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Domain and application configuration hierarchy. На схеме отражено примерно 14 классов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

\newpage

<div style="page-break-before: always;"></div>

## 07-application-core-services — Application Core Services

![07-application-core-services](class-diagrams/png/07-application-core-services.png)

### Описание
Диаграмма Application Core Services показывает архитектурную модель модуля `07-application-core-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: PipelineRunner, BatchExecutor, and their composition. На схеме отражено примерно 16 классов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: PipelineRunner, PipelineServices, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManager.

\newpage

<div style="page-break-before: always;"></div>

## 08-application-services — Application Services

![08-application-services](class-diagrams/png/08-application-services.png)

### Описание
Диаграмма Application Services показывает архитектурную модель модуля `08-application-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: High-level application services. На схеме отражено примерно 19 классов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

\newpage

<div style="page-break-before: always;"></div>

## 08a-application-services-operation-catalog — Application Service Operation Catalog (L2)

![08a-application-services-operation-catalog](class-diagrams/png/08a-application-services-operation-catalog.png)

### Описание
Диаграмма «Application Service Operation Catalog (L2)» описывает модуль `08a-application-services-operation-catalog` и фиксирует ключевые классы, контракты и связи на уровне `Class / Interface`. Основной фокус: Detailed operational methods extracted from 08-application-services L1 overview.

\newpage

<div style="page-break-before: always;"></div>

## 09-transformers — Transformers

![09-transformers](class-diagrams/png/09-transformers.png)

### Описание
Диаграмма Transformers показывает архитектурную модель модуля `09-transformers` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: BaseTransformer hierarchy and provider-specific implementations. На схеме отражено примерно 20 классов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

\newpage

<div style="page-break-before: always;"></div>

## 10-adapters — Infrastructure Adapters

![10-adapters](class-diagrams/png/10-adapters.png)

### Описание
Диаграмма Infrastructure Adapters показывает архитектурную модель модуля `10-adapters` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: HTTP adapter class hierarchy with mixins. На схеме отражено примерно 18 классов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

\newpage

<div style="page-break-before: always;"></div>

## 11-storage — Storage Components

![11-storage](class-diagrams/png/11-storage.png)

### Описание
Диаграмма Storage Components показывает архитектурную модель модуля `11-storage` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Bronze/Silver/Gold writers and supporting classes. На схеме отражено примерно 16 классов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

\newpage

<div style="page-break-before: always;"></div>

## 12-composite-pipeline — Composite Pipeline Components

![12-composite-pipeline](class-diagrams/png/12-composite-pipeline.png)

### Описание
Диаграмма Composite Pipeline Components показывает архитектурную модель модуля `12-composite-pipeline` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Runner, coordinators, merge service, and FSM. На схеме отражено примерно 14 классов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

\newpage

<div style="page-break-before: always;"></div>

## 13-domain-services — Domain Services

![13-domain-services](class-diagrams/png/13-domain-services.png)

### Описание
Диаграмма Domain Services показывает архитектурную модель модуля `13-domain-services` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Pure domain services without I/O. На схеме отражено примерно 10 классов и 0 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

\newpage

<div style="page-break-before: always;"></div>

## 14-observability — Observability Components

![14-observability](class-diagrams/png/14-observability.png)

### Описание
Диаграмма Observability Components показывает архитектурную модель модуля `14-observability` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Logging, metrics, tracing implementations. На схеме отражено примерно 19 классов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

\newpage

<div style="page-break-before: always;"></div>

## 14a-observability-method-catalog — Observability Method Catalog (L2)

![14a-observability-method-catalog](class-diagrams/png/14a-observability-method-catalog.png)

### Описание
Диаграмма «Observability Method Catalog (L2)» описывает модуль `14a-observability-method-catalog` и фиксирует ключевые классы, контракты и связи на уровне `Class / Interface`. Основной фокус: Detailed method surface extracted from 14-observability L1 overview.

\newpage

<div style="page-break-before: always;"></div>

## 15-extractors — Field Extractors

![15-extractors](class-diagrams/png/15-extractors.png)

### Описание
Диаграмма Field Extractors показывает архитектурную модель модуля `15-extractors` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Extractor pattern used in transformers. На схеме отражено примерно 12 классов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

\newpage

<div style="page-break-before: always;"></div>

## 16-factories-bootstrap — Factories & Bootstrap

![16-factories-bootstrap](class-diagrams/png/16-factories-bootstrap.png)

### Описание
Диаграмма Factories & Bootstrap показывает архитектурную модель модуля `16-factories-bootstrap` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Composition layer factories and DI assembly. На схеме отражено примерно 13 классов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: DataSourceRegistry, TransformerFactory, RunnerFactory, DQFactory, RuntimeAssembly, RunnerBootstrap.

---
