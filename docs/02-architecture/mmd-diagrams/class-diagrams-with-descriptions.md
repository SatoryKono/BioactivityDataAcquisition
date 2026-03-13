# BioETL Class Diagrams With Descriptions

- Generated: 2026-03-13T11:52:02
- Diagram count: 19

## Table of Contents

- [01-domain-ports — Class Diagram: Domain Port Protocols](#01-domain-ports)
- [01a-domain-ports-method-catalog — Class Diagram: Domain Port Method Catalog (L2)](#01a-domain-ports-method-catalog)
- [02-entities-aggregates — Class Diagram: Entities & Aggregates](#02-entities-aggregates)
- [03-value-objects — Class Diagram: Value Objects](#03-value-objects)
- [04-types-enums — Class Diagram: Types & Enums](#04-types-enums)
- [05-exceptions — Class Diagram: Exception Hierarchy](#05-exceptions)
- [06-config-classes — Class Diagram: Configuration Classes](#06-config-classes)
- [07-application-core-services — Class Diagram: Application Core Services](#07-application-core-services)
- [08-application-services — Class Diagram: Application Services](#08-application-services)
- [08a-application-services-operation-catalog — Class Diagram: Application Service Operation Catalog (L2)](#08a-application-services-operation-catalog)
- [09-transformers — Class Diagram: Transformers](#09-transformers)
- [10-adapters — Class Diagram: Infrastructure Adapters](#10-adapters)
- [11-storage — Class Diagram: Storage Components](#11-storage)
- [12-composite-pipeline — Class Diagram: Composite Pipeline Components](#12-composite-pipeline)
- [13-domain-services — Class Diagram: Domain Services](#13-domain-services)
- [14-observability — Class Diagram: Observability Components](#14-observability)
- [14a-observability-method-catalog — Class Diagram: Observability Method Catalog (L2)](#14a-observability-method-catalog)
- [15-extractors — Class Diagram: Field Extractors](#15-extractors)
- [16-factories-bootstrap — Class Diagram: Factories & Bootstrap](#16-factories-bootstrap)

\newpage

<div style="page-break-before: always;"></div>

## 01-domain-ports — Class Diagram: Domain Port Protocols

![01-domain-ports](class-diagrams/png/01-domain-ports.png)

### Описание
Диаграмма «Class Diagram: Domain Port Protocols» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: All Protocol interfaces defined in domain/ports/. На схеме отражено примерно 19 узлов и 1 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\newpage

<div style="page-break-before: always;"></div>

## 01a-domain-ports-method-catalog — Class Diagram: Domain Port Method Catalog (L2)

![01a-domain-ports-method-catalog](class-diagrams/png/01a-domain-ports-method-catalog.png)

### Описание
Диаграмма «Class Diagram: Domain Port Method Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed method surface extracted from 01-domain-ports L1 overview.. На схеме отражено примерно 13 узлов и 1 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 02-entities-aggregates — Class Diagram: Entities & Aggregates

![02-entities-aggregates](class-diagrams/png/02-entities-aggregates.png)

### Описание
Диаграмма «Class Diagram: Entities & Aggregates» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain entities, aggregate roots, and their relationships.. На схеме отражено примерно 13 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 03-value-objects — Class Diagram: Value Objects

![03-value-objects](class-diagrams/png/03-value-objects.png)

### Описание
Диаграмма «Class Diagram: Value Objects» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Immutable domain value objects.. На схеме отражено примерно 17 узлов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `17`

\newpage

<div style="page-break-before: always;"></div>

## 04-types-enums — Class Diagram: Types & Enums

![04-types-enums](class-diagrams/png/04-types-enums.png)

### Описание
Диаграмма «Class Diagram: Types & Enums» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: All type aliases, NewTypes, and enumerations.. На схеме отражено примерно 19 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `19`

\newpage

<div style="page-break-before: always;"></div>

## 05-exceptions — Class Diagram: Exception Hierarchy

![05-exceptions](class-diagrams/png/05-exceptions.png)

### Описание
Диаграмма «Class Diagram: Exception Hierarchy» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain exception tree.. На схеме отражено примерно 19 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\newpage

<div style="page-break-before: always;"></div>

## 06-config-classes — Class Diagram: Configuration Classes

![06-config-classes](class-diagrams/png/06-config-classes.png)

### Описание
Диаграмма «Class Diagram: Configuration Classes» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain and application configuration hierarchy.. На схеме отражено примерно 14 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `14`

\newpage

<div style="page-break-before: always;"></div>

## 07-application-core-services — Class Diagram: Application Core Services

![07-application-core-services](class-diagrams/png/07-application-core-services.png)

### Описание
Диаграмма «Class Diagram: Application Core Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: PipelineRunner, BatchExecutor, and their composition.. На схеме отражено примерно 16 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Runner Core, Batch Processing, Execution Managers, Support Services. Показательные узлы для быстрого чтения: PipelineRunner, PipelineServices, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManager.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `16`

\newpage

<div style="page-break-before: always;"></div>

## 08-application-services — Class Diagram: Application Services

![08-application-services](class-diagrams/png/08-application-services.png)

### Описание
Диаграмма «Class Diagram: Application Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: High-level application services.. На схеме отражено примерно 19 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Core Application, Operational Services, DQ Analyzers. Показательные узлы для быстрого чтения: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `19`

\newpage

<div style="page-break-before: always;"></div>

## 08a-application-services-operation-catalog — Class Diagram: Application Service Operation Catalog (L2)

![08a-application-services-operation-catalog](class-diagrams/png/08a-application-services-operation-catalog.png)

### Описание
Диаграмма «Class Diagram: Application Service Operation Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed operational methods extracted from 08-application-services L1 overview.. На схеме отражено примерно 9 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: MedallionLifecycleService, VacuumService, PipelineObserver, CheckpointService, MetricsService, QuarantineService.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `9`

\newpage

<div style="page-break-before: always;"></div>

## 09-transformers — Class Diagram: Transformers

![09-transformers](class-diagrams/png/09-transformers.png)

### Описание
Диаграмма «Class Diagram: Transformers» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: BaseTransformer hierarchy and provider-specific implementations.. На схеме отражено примерно 20 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Base Layer, ChEMBL Transformers, Publication Enrichers, Other Providers. Показательные узлы для быстрого чтения: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `20`

\newpage

<div style="page-break-before: always;"></div>

## 10-adapters — Class Diagram: Infrastructure Adapters

![10-adapters](class-diagrams/png/10-adapters.png)

### Описание
Диаграмма «Class Diagram: Infrastructure Adapters» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: HTTP adapter class hierarchy with mixins.. На схеме отражено примерно 18 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-08`
- Узлы (metadata): `18`

\newpage

<div style="page-break-before: always;"></div>

## 11-storage — Class Diagram: Storage Components

![11-storage](class-diagrams/png/11-storage.png)

### Описание
Диаграмма «Class Diagram: Storage Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers and supporting classes.. На схеме отражено примерно 16 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-01`
- Узлы (metadata): `16`

\newpage

<div style="page-break-before: always;"></div>

## 12-composite-pipeline — Class Diagram: Composite Pipeline Components

![12-composite-pipeline](class-diagrams/png/12-composite-pipeline.png)

### Описание
Диаграмма «Class Diagram: Composite Pipeline Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Runner, coordinators, merge service, and FSM.. На схеме отражено примерно 14 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-01`
- Узлы (metadata): `14`

\newpage

<div style="page-break-before: always;"></div>

## 13-domain-services — Class Diagram: Domain Services

![13-domain-services](class-diagrams/png/13-domain-services.png)

### Описание
Диаграмма «Class Diagram: Domain Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Pure domain services without I/O.. На схеме отражено примерно 10 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `10`

\newpage

<div style="page-break-before: always;"></div>

## 14-observability — Class Diagram: Observability Components

![14-observability](class-diagrams/png/14-observability.png)

### Описание
Диаграмма «Class Diagram: Observability Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Logging, metrics, tracing implementations.. На схеме отражено примерно 19 узлов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\newpage

<div style="page-break-before: always;"></div>

## 14a-observability-method-catalog — Class Diagram: Observability Method Catalog (L2)

![14a-observability-method-catalog](class-diagrams/png/14a-observability-method-catalog.png)

### Описание
Диаграмма «Class Diagram: Observability Method Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed method surface extracted from 14-observability L1 overview.. На схеме отражено примерно 9 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: LoggerPort, UnifiedLogger, MetricsPort, MetricsCollector, PrometheusMetrics, MetricsServerAdapter.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `9`

\newpage

<div style="page-break-before: always;"></div>

## 15-extractors — Class Diagram: Field Extractors

![15-extractors](class-diagrams/png/15-extractors.png)

### Описание
Диаграмма «Class Diagram: Field Extractors» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Extractor pattern used in transformers.. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: PubMedExtractors, UniProtExtractors. Показательные узлы для быстрого чтения: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 16-factories-bootstrap — Class Diagram: Factories & Bootstrap

![16-factories-bootstrap](class-diagrams/png/16-factories-bootstrap.png)

### Описание
Диаграмма «Class Diagram: Factories & Bootstrap» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Composition layer factories and DI assembly.. На схеме отражено примерно 13 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: DataSourceRegistry, TransformerFactory, RunnerFactory, DQFactory, RuntimeAssembly, RunnerBootstrap.

### Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `13`
