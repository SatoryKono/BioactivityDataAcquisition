______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram Descriptions

Обновлено: 2026-03-20

Этот файл служит обзорной narrative-картой по семействам class-диаграмм. Он помогает ориентироваться в canonical families и representative slices, но не является точным инвентарём текущего числа классов или связей.

Отдельно от этой narrative-карты публикуется supplemental generated layer:
AST-derived package-family class diagrams (`90-pkg-*.mmd`) для всех
`src/bioetl/**` families с более чем тремя top-level classes, которые не были
покрыты curated family set. Этот generated слой расширяет coverage class
diagrams, но сам `class-summary.md` по-прежнему остаётся curated narrative
обзором, а не inventory-реестром.

## 01-domain-ports — Domain Port Protocols

Диаграмма «Domain Port Protocols» описывает модуль `01-domain-ports` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: all protocol interfaces defined in `domain/ports`, включая narrow storage ports и backward-compatible aggregate `StoragePort`. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

## 01a-domain-ports-method-catalog — Domain Port Method Catalog (L2)

Диаграмма «Domain Port Method Catalog (L2)» описывает модуль `01a-domain-ports-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 01-domain-ports L1 overview. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

## 02-entities-aggregates — Entities & Aggregates

Диаграмма «Entities & Aggregates» описывает модуль `02-entities-aggregates` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain entities, aggregate roots, and their relationships. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

## 03-value-objects — Value Objects

Диаграмма «Value Objects» описывает модуль `03-value-objects` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Immutable domain value objects. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

## 04-types-enums — Types & Enums

Диаграмма «Types & Enums» описывает модуль `04-types-enums` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: All type aliases, NewTypes, and enumerations. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

## 05-exceptions — Exception Hierarchy

Диаграмма «Exception Hierarchy» описывает модуль `05-exceptions` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain exception tree. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

## 06-config-classes — Configuration Classes

Диаграмма «Configuration Classes» описывает модуль `06-config-classes` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Domain and application configuration hierarchy. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

## 07-application-core-services — Application Core Services

Диаграмма «Application Core Services» описывает application-core orchestration и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: runner, batch-execution, lifecycle, preflight и postrun service families внутри `application/core`. Для быстрого чтения и ревью полезно начать с элементов: PipelineRunner, BatchExecutor, RecordProcessor, BatchWriter, CheckpointManagerService, BatchMemoryManagerService, BatchMetricsRecorderService, BatchTracingManagerService, PreflightService, PostrunService.

## 08-application-services — Application Services

Диаграмма «Application Services» описывает модуль `08-application-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: High-level application services. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

## 08a-application-services-operation-catalog — Application Service Operation Catalog (L2)

Диаграмма «Application Service Operation Catalog (L2)» описывает модуль `08a-application-services-operation-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed operational methods extracted from 08-application-services L1 overview. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: MedallionLifecycleService, VacuumService, PipelineObserver, CheckpointService, MetricsService, QuarantineService.

## 09-transformers — Transformers

Диаграмма «Transformers» описывает модуль `09-transformers` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: BaseTransformer hierarchy and provider-specific implementations. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

## 10-adapters — Infrastructure Adapters

Диаграмма «Infrastructure Adapters» описывает модуль `10-adapters` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: HTTP adapter class hierarchy with mixins. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

## 11-storage — Storage Components

Диаграмма «Storage Components» описывает модуль `11-storage` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Bronze/Silver/Gold writers and supporting classes. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

## 12-composite-pipeline — Composite Pipeline Components

Диаграмма «Composite Pipeline Components» описывает модуль `12-composite-pipeline` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Runner, coordinators, merge service, and FSM. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

## 13-domain-services — Domain Services

Диаграмма «Domain Services» описывает модуль `13-domain-services` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Pure domain services without I/O. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

## 14-observability — Observability Components

Диаграмма «Observability Components» описывает модуль `14-observability` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Logging, metrics, tracing implementations. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

## 14a-observability-method-catalog — Observability Method Catalog (L2)

Диаграмма «Observability Method Catalog (L2)» описывает модуль `14a-observability-method-catalog` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Detailed method surface extracted from 14-observability L1 overview. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: LoggerPort, UnifiedLogger, MetricsPort, MetricsCollector, PrometheusMetrics, MetricsServerAdapter.

## 15-extractors — Field Extractors

Диаграмма «Field Extractors» описывает модуль `15-extractors` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: Extractor pattern used in transformers. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: BaseFieldExtractor, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor, IdentifierExtractor.

## 16-factories-bootstrap — Factories & Bootstrap

Диаграмма «Factories & Bootstrap» описывает модуль `16-factories-bootstrap` и фиксирует архитектурные границы, основные роли классов и характер их взаимодействий. Основной фокус: current composition-layer factories, provider registry, and runtime assembly seams. Схема используется как representative family-level overview, а не как исчерпывающий инвентарь текущей кодовой поверхности. Для быстрого чтения и ревью полезно начать с элементов: ProviderRegistry, DataSourceFactory, PipelineRegistry, RunnerFactory, RunnerFactoryBuilderService, CompositeSupportServicesFactory.
