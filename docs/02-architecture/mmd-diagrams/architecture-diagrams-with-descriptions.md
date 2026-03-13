# BioETL Architecture Diagrams With Descriptions

- Generated: 2026-03-13T11:52:02
- Diagram count: 52

## Table of Contents

- [01-high-level-hexagonal — High-Level Hexagonal Architecture](#01-high-level-hexagonal)
- [01a-hexagonal-overview — Hexagonal Overview](#01a-hexagonal-overview)
- [01b-hexagonal-domain-app — Hexagonal Domain and Application](#01b-hexagonal-domain-app)
- [01c-hexagonal-infra-comp — Hexagonal Infrastructure and Composition](#01c-hexagonal-infra-comp)
- [01d-hexagonal-overview-rounded — Hexagonal Overview (Rounded Nodes)](#01d-hexagonal-overview-rounded)
- [02-layer-dependency-matrix — Layer Dependency Matrix (ARCH-001)](#02-layer-dependency-matrix)
- [03-medallion-data-flow — Medallion Architecture Data Flow (Bronze → Silver → Gold)](#03-medallion-data-flow)
- [03a-medallion-layers-overview — Medallion Layers Overview](#03a-medallion-layers-overview)
- [04-pipeline-execution-flow — Pipeline Execution Lifecycle](#04-pipeline-execution-flow)
- [05-provider-adapter-hierarchy — Provider Adapter Hierarchy](#05-provider-adapter-hierarchy)
- [05a-adapter-hierarchy-base — Adapter Hierarchy: Base Types](#05a-adapter-hierarchy-base)
- [05b-adapter-hierarchy-providers — Adapter Hierarchy: Provider Implementations](#05b-adapter-hierarchy-providers)
- [06-storage-layer — Storage Layer Components](#06-storage-layer)
- [06a-storage-writers — Storage Writers](#06a-storage-writers)
- [06b-storage-support — Storage Support Components](#06b-storage-support)
- [07-dq-system — Data Quality (DQ) System](#07-dq-system)
- [07a-dq-analysis — DQ Analysis Services](#07a-dq-analysis)
- [07b-dq-pipeline — DQ Pipeline Integration](#07b-dq-pipeline)
- [08-composite-pipeline — Composite Pipeline Architecture](#08-composite-pipeline)
- [08a-composite-config — Composite Pipeline Configuration & FSM](#08a-composite-config)
- [08b-composite-execution — Composite Pipeline Execution](#08b-composite-execution)
- [09-observability-stack — Observability Stack](#09-observability-stack)
- [09a-observability-app — Observability: Application Layer](#09a-observability-app)
- [09b-observability-infra — Observability: Infrastructure Layer](#09b-observability-infra)
- [10-resilience-patterns — Resilience Patterns](#10-resilience-patterns)
- [11-configuration-system — Configuration System](#11-configuration-system)
- [11a-config-loading — Configuration: Loading Pipeline](#11a-config-loading)
- [11b-config-domain — Configuration: Domain & Application Config](#11b-config-domain)
- [12-bootstrap-di-container — Bootstrap / DI Container (Composition Root)](#12-bootstrap-di-container)
- [12a-bootstrap-factories — Bootstrap: Factories and Registries](#12a-bootstrap-factories)
- [12b-bootstrap-wiring — Bootstrap: Wiring Graph](#12b-bootstrap-wiring)
- [13-port-protocol-contracts — Port/Protocol Contracts (Full Map)](#13-port-protocol-contracts)
- [13a-data-storage-ports — DataSource and Storage Ports](#13a-data-storage-ports)
- [13a-port-contracts-data-sources — Port Contracts: Data Sources](#13a-port-contracts-data-sources)
- [13b-operational-ports — Operational and Observability Ports](#13b-operational-ports)
- [13b-port-contracts-storage — Port Contracts: Storage](#13b-port-contracts-storage)
- [13c-port-contracts-observability — Port Contracts: Observability and Resilience](#13c-port-contracts-observability)
- [13c-validation-dq-ports — Validation and Data Quality Ports](#13c-validation-dq-ports)
- [13d-port-contracts-services — Port Contracts: Services and Controls](#13d-port-contracts-services)
- [13e-operational-ports-domain — Domain Operational Ports](#13e-operational-ports-domain)
- [13f-operational-ports-infra — Infrastructure Operational Implementations](#13f-operational-ports-infra)
- [14-cli-interface-layer — CLI / Interface Layer](#14-cli-interface-layer)
- [14a-cli-commands — CLI: Command Structure](#14a-cli-commands)
- [14b-cli-routing — CLI: Routing to Composition & Application](#14b-cli-routing)
- [15-batch-executor-internals — BatchExecutor Internal Architecture](#15-batch-executor-internals)
- [16-transformer-hierarchy — Transformer Hierarchy](#16-transformer-hierarchy)
- [16a-transformer-base — Base Transformer and ChEMBL Transformers](#16a-transformer-base)
- [16b-transformer-pub-other — Publication, UniProt, Other Transformers and Extractors](#16b-transformer-pub-other)
- [17-security-pii-audit — Security, PII Hashing, and Audit Trail](#17-security-pii-audit)
- [18-lock-checkpoint-shutdown — Locking, Checkpoint, and Graceful Shutdown](#18-lock-checkpoint-shutdown)
- [18a-lock-system — Lock System](#18a-lock-system)
- [18b-checkpoint-shutdown — Checkpoint and Shutdown System](#18b-checkpoint-shutdown)

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-hexagonal — High-Level Hexagonal Architecture

![01-high-level-hexagonal](architecture/png/01-high-level-hexagonal.png)

### Описание
Диаграмма «High-Level Hexagonal Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: the Ports & Adapters (Hexagonal) pattern across all layers.. На схеме отражено примерно 46 узлов и 29 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External Systems, External APIs, interfaces layer, composition layer, application layer, domain layer (pure, no I/O). Показательные узлы для быстрого чтения: ChEMBL, PubMed, UniProt, PubChem, CrossRef, OpenAlex. Примечание: Decomposed into 01a, 01b, 01c sub-diagrams.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `46`

\newpage

<div style="page-break-before: always;"></div>

## 01a-hexagonal-overview — Hexagonal Overview

![01a-hexagonal-overview](architecture/png/01a-hexagonal-overview.png)

### Описание
Диаграмма «Hexagonal Overview» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers 5 architectural layers, external systems, and main dependency directions.. На схеме отражено примерно 11 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI Commands (Click), Orchestration, Bootstrap / Assembly, Application Core, Port Protocols, Provider Adapters.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `11`

\newpage

<div style="page-break-before: always;"></div>

## 01b-hexagonal-domain-app — Hexagonal Domain and Application

![01b-hexagonal-domain-app](architecture/png/01b-hexagonal-domain-app.png)

### Описание
Диаграмма «Hexagonal Domain and Application» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers domain contracts and core application services that depend on them.. На схеме отражено примерно 13 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Domain Layer. Показательные узлы для быстрого чтения: Core (Runner, Executor, Transformer, Writer), Services (DQ, Export, Health, Lifecycle), Composite Pipeline (Coordinator, Merger, FSM), Pipeline Transformers (per provider), PipelineObserver, Port Protocols.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 01c-hexagonal-infra-comp — Hexagonal Infrastructure and Composition

![01c-hexagonal-infra-comp](architecture/png/01c-hexagonal-infra-comp.png)

### Описание
Диаграмма «Hexagonal Infrastructure and Composition» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers infrastructure adapters and composition-root wiring points.. На схеме отражено примерно 14 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Composition Layer, Infrastructure Layer, Domain Layer. Показательные узлы для быстрого чтения: Bootstrap / Assembly, Factories, Provider Registry, Runtime Builders, HTTP Adapters, Storage.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `14`

\newpage

<div style="page-break-before: always;"></div>

## 01d-hexagonal-overview-rounded — Hexagonal Overview (Rounded Nodes)

![01d-hexagonal-overview-rounded](architecture/png/01d-hexagonal-overview-rounded.png)

### Описание
Диаграмма «Hexagonal Overview (Rounded Nodes)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers 5 architectural layers, external systems, and main dependency directions.. На схеме отражено примерно 11 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI Commands (Click), Orchestration, Bootstrap / Assembly, Application Core, Port Protocols, Provider Adapters.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-01`
- Узлы (metadata): `11`

\newpage

<div style="page-break-before: always;"></div>

## 02-layer-dependency-matrix — Layer Dependency Matrix (ARCH-001)

![02-layer-dependency-matrix](architecture/png/02-layer-dependency-matrix.png)

### Описание
Диаграмма «Layer Dependency Matrix (ARCH-001)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Enforced import boundaries between architectural layers.. На схеме отражено примерно 5 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Legend, Architectural Layers. Показательные узлы для быстрого чтения: ✅ Allowed, ❌ Forbidden, domain (pure business logic, no I/O, no frameworks), application (use cases, orchestration, transformers), infrastructure (adapters, storage, observability), composition (DI wiring, factories, bootstrap).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `5`

\newpage

<div style="page-break-before: always;"></div>

## 03-medallion-data-flow — Medallion Architecture Data Flow (Bronze → Silver → Gold)

![03-medallion-data-flow](architecture/png/03-medallion-data-flow.png)

### Описание
Диаграмма «Medallion Architecture Data Flow (Bronze → Silver → Gold)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how data flows through the three medallion layers.. На схеме отражено примерно 36 узлов и 31 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External Data Sources, Data Ingestion, Bronze Layer (Raw), Transformation, Silver Layer (Normalized), Gold Transformation. Показательные узлы для быстрого чтения: Semantic Scholar API, DataSourcePort fetch() / fetch_filtered(), RateLimiter (TokenBucket), CircuitBreaker, Retry Logic, BronzeWriter. Примечание: Canonical medallion flow — at threshold boundary.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `36`

\newpage

<div style="page-break-before: always;"></div>

## 03a-medallion-layers-overview — Medallion Layers Overview

![03a-medallion-layers-overview](architecture/png/03a-medallion-layers-overview.png)

### Описание
Диаграмма «Medallion Layers Overview» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Compact decomposition view for 03-medallion-data-flow.mmd (layer-level semantics). На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Ingestion, Processing, Serving. Показательные узлы для быстрого чтения: Provider APIs, Bronze Layer\nRaw JSON, Normalize + Validate, Silver Layer\nDelta Tables, DQ Checks, Quarantine. Связанный ADR: ADR-002, ADR-040.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`
- ADR: `ADR-002, ADR-040`

\newpage

<div style="page-break-before: always;"></div>

## 04-pipeline-execution-flow — Pipeline Execution Lifecycle

![04-pipeline-execution-flow](architecture/png/04-pipeline-execution-flow.png)

### Описание
Диаграмма «Pipeline Execution Lifecycle» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Sequence of phases in a single pipeline run.. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга.

### Метаданные
- Тип: `sequenceDiagram`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 05-provider-adapter-hierarchy — Provider Adapter Hierarchy

![05-provider-adapter-hierarchy](architecture/png/05-provider-adapter-hierarchy.png)

### Описание
Диаграмма «Provider Adapter Hierarchy» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how each provider adapter inherits from base classes and implements DataSourcePort.. На схеме отражено примерно 27 узлов и 24 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Mixins, Base Adapters, ChEMBL, PubMed, UniProt. Показательные узлы для быстрого чтения: DataSourcePort (Protocol), HealthCheckPort (Protocol), HealthCheckMixin, HealthCheckProviderMixin, NotSupportedMultiFilterMixin, DelegatingFallbackMixin. Примечание: Decomposed into 05a, 05b sub-diagrams.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `27`

\newpage

<div style="page-break-before: always;"></div>

## 05a-adapter-hierarchy-base — Adapter Hierarchy: Base Types

![05a-adapter-hierarchy-base](architecture/png/05a-adapter-hierarchy-base.png)

### Описание
Диаграмма «Adapter Hierarchy: Base Types» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers core ports, base adapters, reusable mixins, and adapter decorators.. На схеме отражено примерно 12 узлов и 8 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, HealthCheckPort, HealthCheckProviderMixin, NotSupportedMultiFilterMixin, FilterableStubMixin, PaginatedFetcherMixin.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 05b-adapter-hierarchy-providers — Adapter Hierarchy: Provider Implementations

![05b-adapter-hierarchy-providers](architecture/png/05b-adapter-hierarchy-providers.png)

### Описание
Диаграмма «Adapter Hierarchy: Provider Implementations» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers concrete provider adapters and provider-specific mixins.. На схеме отражено примерно 15 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Layer. Показательные узлы для быстрого чтения: BaseHttpAdapter, BaseSyncAdapter, ChemblAdapter, PubMedAdapter, UniProtAdapter, CrossRefAdapter.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `15`

\newpage

<div style="page-break-before: always;"></div>

## 06-storage-layer — Storage Layer Components

![06-storage-layer](architecture/png/06-storage-layer.png)

### Описание
Диаграмма «Storage Layer Components» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers, Delta Lake, metadata, and validation.. На схеме отражено примерно 21 узлов и 23 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Port, Storage Writers, Bronze Storage, Silver Storage, Gold Storage, Delta Reader. Показательные узлы для быстрого чтения: StoragePort (Protocol), AtomicWriteGroup ━━━━━━━━━━━━━━━━━ Atomic multi-file writes with rollback, GoldWriter csv_exporter + audit + metadata_writer write_gold / clear_gold, ArrowDataConverter (records → PyArrow), RetentionPolicy (vacuum/retention), MetadataWriter (_metadata.yaml). Примечание: Decomposed into 06a-storage-writers, 06b-storage-support.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `21`

\newpage

<div style="page-break-before: always;"></div>

## 06a-storage-writers — Storage Writers

![06a-storage-writers](architecture/png/06a-storage-writers.png)

### Описание
Диаграмма «Storage Writers» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers with Delta Lake base class, port contract, and file system layout.. На схеме отражено примерно 10 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Port, Bronze Storage, Silver Storage, Gold Storage, Delta Reader, File System Layout. Показательные узлы для быстрого чтения: StoragePort (Protocol), BronzeWriter write_bronze() / aclose(), AtomicWriteGroup atomic multi-file writes, BaseDeltaWriter get_table_path() / clear(), SilverWriter write_silver() / merge_silver(), GoldWriter write_gold() / clear_gold().

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `10`

\newpage

<div style="page-break-before: always;"></div>

## 06b-storage-support — Storage Support Components

![06b-storage-support](architecture/png/06b-storage-support.png)

### Описание
Диаграмма «Storage Support Components» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Support utilities, validators, and metadata builders for the storage layer.. На схеме отражено примерно 11 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Support Components, Validation, Metadata Builders. Показательные узлы для быстрого чтения: ArrowDataConverter records → PyArrow, RetentionPolicy vacuum / retention, MetadataWriter _metadata.yaml, CsvExporter Delta → CSV export, DQReportWriter DQ reports JSON, PanderaSilverValidator SilverValidatorPort impl.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `11`

\newpage

<div style="page-break-before: always;"></div>

## 07-dq-system — Data Quality (DQ) System

![07-dq-system](architecture/png/07-dq-system.png)

### Описание
Диаграмма «Data Quality (DQ) System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: DQ monitoring, analysis, and reporting across all medallion layers.. На схеме отражено примерно 22 узлов и 24 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Application Services, Application DQ Analysis, Pipeline Integration, Domain Value Objects, Infrastructure Implementations. Показательные узлы для быстрого чтения: DQMonitorPort, BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort, DataQualityService -------- + evaluate(context, executor). Примечание: Decomposed into 07a-dq-analysis, 07b-dq-pipeline.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `22`

\newpage

<div style="page-break-before: always;"></div>

## 07a-dq-analysis — DQ Analysis Services

![07a-dq-analysis](architecture/png/07a-dq-analysis.png)

### Описание
Диаграмма «DQ Analysis Services» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Domain ports, application services, analyzers, and anomaly detection for Data Quality.. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Application Services, DQ Analyzers, Anomaly Detection. Показательные узлы для быстрого чтения: DQMonitorPort, BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort, DataQualityService evaluate(context, executor).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 07b-dq-pipeline — DQ Pipeline Integration

![07b-dq-pipeline](architecture/png/07b-dq-pipeline.png)

### Описание
Диаграмма «DQ Pipeline Integration» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Pipeline DQ checks, domain value objects, and infrastructure config/report writers.. На схеме отражено примерно 10 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Pipeline Integration, Domain Value Objects, Infrastructure Implementations. Показательные узлы для быстрого чтения: BatchTransformer _check_dq_thresholds(), QuarantineManager quarantines failed records, ErrorClassifier recoverable vs fatal, DQMetrics null_rate / duplicate_rate, DQResult passed / error_rate, DQReport layer / table_name / results.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `10`

\newpage

<div style="page-break-before: always;"></div>

## 08-composite-pipeline — Composite Pipeline Architecture

![08-composite-pipeline](architecture/png/08-composite-pipeline.png)

### Описание
Диаграмма «Composite Pipeline Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: seed → dependencies → enrichers (parallel) → merge flow.. На схеме отражено примерно 33 узлов и 34 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Composite Configuration, CompositePipelineRunner, State Machine, Execution Components, Dependencies (Sequential), Enrichers (Parallel Fan-Out). Показательные узлы для быстрого чтения: CompositeConfig, SeedConfig, DependencyConfig, EnricherConfig, MergeConfig, Config overview seed + dependencies enrichers + merge. Примечание: Decomposed into 08a-composite-config, 08b-composite-execution.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `33`

\newpage

<div style="page-break-before: always;"></div>

## 08a-composite-config — Composite Pipeline Configuration & FSM

![08a-composite-config](architecture/png/08a-composite-config.png)

### Описание
Диаграмма «Composite Pipeline Configuration & FSM» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Config hierarchy (CompositeConfig → sub-configs) and execution state machine.. На схеме отражено примерно 13 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Composite Configuration, State Machine. Показательные узлы для быстрого чтения: CompositeConfig name / seed / deps / enrichers / merge, SeedConfig, DependencyConfig, EnricherConfig, MergeConfig, Config Details: seed → deps → enrichers → merge.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 08b-composite-execution — Composite Pipeline Execution

![08b-composite-execution](architecture/png/08b-composite-execution.png)

### Описание
Диаграмма «Composite Pipeline Execution» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Runner orchestration: seed → deps → enrichers (parallel) → merge, with checkpointing and cross-validation.. На схеме отражено примерно 20 узлов и 20 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: CompositePipelineRunner, Preflight, Execution Components, Dependencies (Sequential), Enrichers (Parallel Fan-Out), Merge Phase. Показательные узлы для быстрого чтения: CompositePipelineRunner orchestrates full execution, PreflightValidator, Seed Pipeline, DependencyCoordinator, Dependency 1, EnrichmentCoordinator.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\newpage

<div style="page-break-before: always;"></div>

## 09-observability-stack — Observability Stack

![09-observability-stack](architecture/png/09-observability-stack.png)

### Описание
Диаграмма «Observability Stack» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Logging, Metrics, Tracing architecture.. На схеме отражено примерно 24 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Application Observability, Infrastructure: Logging, Infrastructure: Metrics, Infrastructure: Tracing, Infrastructure: Anomaly Detection. Показательные узлы для быстрого чтения: LoggerPort (Protocol) bind + info/warn/error/debug/exception, MetricsPort (Protocol) observe_histogram + increment_counter set_gauge + close, TracingPort (Protocol) get_tracer + close, DQMonitorPort (Protocol) add_metric + check_quality update_baseline, PipelineObserver logger + metrics + tracing hooks, BatchMetricsRecorder track size/processed/error/quarantine. Примечание: Decomposed into 09a-observability-app, 09b-observability-infra.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `24`

\newpage

<div style="page-break-before: always;"></div>

## 09a-observability-app — Observability: Application Layer

![09a-observability-app](architecture/png/09a-observability-app.png)

### Описание
Диаграмма «Observability: Application Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Application-level observability: ports, pipeline observer, batch metrics, adapter metrics.. На схеме отражено примерно 8 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Application Observability, Adapter-Level Metrics. Показательные узлы для быстрого чтения: LoggerPort (Protocol), MetricsPort (Protocol), TracingPort (Protocol), DQMonitorPort (Protocol), PipelineObserver, BatchMetricsRecorder.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `8`

\newpage

<div style="page-break-before: always;"></div>

## 09b-observability-infra — Observability: Infrastructure Layer

![09b-observability-infra](architecture/png/09b-observability-infra.png)

### Описание
Диаграмма «Observability: Infrastructure Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Infrastructure implementations: logging, metrics, tracing, anomaly detection, external systems.. На схеме отражено примерно 13 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure: Logging, Infrastructure: Metrics, Infrastructure: Tracing, Infrastructure: Anomaly Detection, External Systems. Показательные узлы для быстрого чтения: UnifiedLogger (impl LoggerPort), MetricsCollector (impl MetricsPort), PrometheusMetrics (impl MetricsPort), MetricsServerAdapter, NoOpMetrics, OpenTelemetryTracer (impl TracingPort).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 10-resilience-patterns — Resilience Patterns

![10-resilience-patterns](architecture/png/10-resilience-patterns.png)

### Описание
Диаграмма «Resilience Patterns» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Circuit Breaker, Rate Limiter, Retry, Health Check patterns.. На схеме отражено примерно 15 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Circuit Breaker Pattern, State Machine, Rate Limiter (Token Bucket), Provider Rate Limits, Retry Logic. Показательные узлы для быстрого чтения: CircuitBreakerPort (Protocol) -------- + get_state() + call(fn), RateLimiterPort (Protocol) -------- + acquire(tokens) + try_acquire(), HealthCheckPort (Protocol) -------- + check_health(), CircuitBreaker -------- provider failure_threshold recovery_timeout, CLOSED (normal operation), OPEN (fail fast).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `15`

\newpage

<div style="page-break-before: always;"></div>

## 11-configuration-system — Configuration System

![11-configuration-system](architecture/png/11-configuration-system.png)

### Описание
Диаграмма «Configuration System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how YAML configs are loaded, validated, and used across the system.. На схеме отражено примерно 29 узлов и 20 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic), Domain Configuration, Composite Domain Config, Application Config. Показательные узлы для быстрого чтения: configs/entities/*/*.yaml pipeline configs, configs/quality/*.yaml DQ rules, configs/filters/*.yaml filter configs, configs/composites/*.yaml composite configs, configs/field_groups/*.yaml field groups, PipelineConfigLoader load(path) -> PipelineConfig. Примечание: Decomposed into 11a-config-loading, 11b-config-domain.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `29`

\newpage

<div style="page-break-before: always;"></div>

## 11a-config-loading — Configuration: Loading Pipeline

![11a-config-loading](architecture/png/11a-config-loading.png)

### Описание
Диаграмма «Configuration: Loading Pipeline» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: YAML files, config loaders, and infrastructure schemas (Pydantic validation).. На схеме отражено примерно 13 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic). Показательные узлы для быстрого чтения: configs/entities/*/*.yaml, configs/quality/*.yaml, configs/filters/*.yaml, configs/composites/*.yaml, configs/field_groups/*.yaml, BaseConfigLoader.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `13`

\newpage

<div style="page-break-before: always;"></div>

## 11b-config-domain — Configuration: Domain & Application Config

![11b-config-domain](architecture/png/11b-config-domain.png)

### Описание
Диаграмма «Configuration: Domain & Application Config» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Domain config objects, composite config, application config, and infrastructure settings.. На схеме отражено примерно 16 узлов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Schemas, Domain Configuration, Composite Domain Config, Application Config, Infrastructure Settings. Показательные узлы для быстрого чтения: ApiConfig, SourceConfig, CircuitBreakerConfig, PipelineContractPolicy, PipelineConfig, TableConfig.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `16`

\newpage

<div style="page-break-before: always;"></div>

## 12-bootstrap-di-container — Bootstrap / DI Container (Composition Root)

![12-bootstrap-di-container](architecture/png/12-bootstrap-di-container.png)

### Описание
Диаграмма «Bootstrap / DI Container (Composition Root)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how dependencies are assembled and wired together.. На схеме отражено примерно 29 узлов и 38 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Entry Points, composition layer, Bootstrap Assembly, Factories, Provider Registry, Runtime Builders. Показательные узлы для быстрого чтения: CLI Commands (Click), HTTP Interface, RuntimeAssembly central DI wiring point creates infra + app components, RunnerBootstrap ━━━━━━━━━━━━━━━━━ + assemble_runner(), StorageBootstrap ━━━━━━━━━━━━━━━━━ + assemble_storage(), HealthBootstrap ━━━━━━━━━━━━━━━━━ + assemble_health(). Примечание: Decomposed into 12a, 12b sub-diagrams.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `29`

\newpage

<div style="page-break-before: always;"></div>

## 12a-bootstrap-factories — Bootstrap: Factories and Registries

![12a-bootstrap-factories](architecture/png/12a-bootstrap-factories.png)

### Описание
Диаграмма «Bootstrap: Factories and Registries» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers composition root factories, provider registry, and builder assembly.. На схеме отражено примерно 10 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer. Показательные узлы для быстрого чтения: CLI Commands (Click), HTTP Interface, bootstrap_pipeline_runner, DataSourceRegistry, GenericPipelineFactory, RunnerFactory.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `10`

\newpage

<div style="page-break-before: always;"></div>

## 12b-bootstrap-wiring — Bootstrap: Wiring Graph

![12b-bootstrap-wiring](architecture/png/12b-bootstrap-wiring.png)

### Описание
Диаграмма «Bootstrap: Wiring Graph» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers runtime assembly sequence and main dependency injection graph.. На схеме отражено примерно 15 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Composition Layer, Infrastructure Layer, Application Layer. Показательные узлы для быстрого чтения: bootstrap_pipeline_runner, RunnerBootstrap, StorageBootstrap, CheckpointBootstrap, LockBootstrap, Provider Adapter (DataSourcePort).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `15`

\newpage

<div style="page-break-before: always;"></div>

## 13-port-protocol-contracts — Port/Protocol Contracts (Full Map)

![13-port-protocol-contracts](architecture/png/13-port-protocol-contracts.png)

### Описание
Диаграмма «Port/Protocol Contracts (Full Map)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: All domain Ports and their infrastructure implementations.. На схеме отражено примерно 68 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports (Protocols), Infrastructure Implementations, Application Implementations. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort. Примечание: Decomposed into 13a, 13b, 13c, 13d sub-diagrams.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `68`

\newpage

<div style="page-break-before: always;"></div>

## 13a-data-storage-ports — DataSource and Storage Ports

![13a-data-storage-ports](architecture/png/13a-data-storage-ports.png)

### Описание
Диаграмма «DataSource and Storage Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: All data acquisition and storage ports.. На схеме отражено примерно 20 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Implementations. Показательные узлы для быстрого чтения: fa:fa-plug DataSourcePort, fa:fa-filter FilterableDataSourcePort, fa:fa-database StoragePort, fa:fa-book-open DeltaReaderPort, fa:fa-file-import InputFilterPort, ChemblAdapter.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\newpage

<div style="page-break-before: always;"></div>

## 13a-port-contracts-data-sources — Port Contracts: Data Sources

![13a-port-contracts-data-sources](architecture/png/13a-port-contracts-data-sources.png)

### Описание
Диаграмма «Port Contracts: Data Sources» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers DataSourcePort and FilterableDataSourcePort implementations per provider.. На схеме отражено примерно 9 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, ChemblAdapter.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `9`

\newpage

<div style="page-break-before: always;"></div>

## 13b-operational-ports — Operational and Observability Ports

![13b-operational-ports](architecture/png/13b-operational-ports.png)

### Описание
Диаграмма «Operational and Observability Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Monitoring, logging, and operational control ports.. На схеме отражено примерно 25 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Implementations. Показательные узлы для быстрого чтения: fa:fa-lock LockPort, fa:fa-flag CheckpointPort, fa:fa-list LoggerPort, fa:fa-chart-line MetricsPort, fa:fa-wave-square TracingPort, fa:fa-bolt CircuitBreakerPort. Примечание: Decomposed into 13e-operational-ports-domain, 13f-operational-ports-infra.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `25`

\newpage

<div style="page-break-before: always;"></div>

## 13b-port-contracts-storage — Port Contracts: Storage

![13b-port-contracts-storage](architecture/png/13b-port-contracts-storage.png)

### Описание
Диаграмма «Port Contracts: Storage» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers StoragePort, DeltaReaderPort, and MetadataWriterPort implementations.. На схеме отражено примерно 9 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: StoragePort, DeltaReaderPort, MetadataWriterPort, BronzeWriter, DeltaReader, MetadataWriter.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `9`

\newpage

<div style="page-break-before: always;"></div>

## 13c-port-contracts-observability — Port Contracts: Observability and Resilience

![13c-port-contracts-observability](architecture/png/13c-port-contracts-observability.png)

### Описание
Диаграмма «Port Contracts: Observability and Resilience» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers Logger/Metrics/Tracing ports plus resilience control ports.. На схеме отражено примерно 15 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: LoggerPort, MetricsPort, TracingPort, CircuitBreakerPort, RateLimiterPort, UnifiedLogger.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `15`

\newpage

<div style="page-break-before: always;"></div>

## 13c-validation-dq-ports — Validation and Data Quality Ports

![13c-validation-dq-ports](architecture/png/13c-validation-dq-ports.png)

### Описание
Диаграмма «Validation and Data Quality Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Ports for ensuring data correctness and quality reporting.. На схеме отражено примерно 20 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Infrastructure, Application. Показательные узлы для быстрого чтения: SilverValidatorPort, GoldValidatorPort, BronzeDQ AnalyzerPort, SilverDQ AnalyzerPort, GoldDQ AnalyzerPort, DQReportWriterPort.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\newpage

<div style="page-break-before: always;"></div>

## 13d-port-contracts-services — Port Contracts: Services and Controls

![13d-port-contracts-services](architecture/png/13d-port-contracts-services.png)

### Описание
Диаграмма «Port Contracts: Services and Controls» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers control ports, data quality service ports, and related implementations.. На схеме отражено примерно 20 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Application Layer, NoOp Implementations (fallback defaults). Показательные узлы для быстрого чтения: LockPort, CheckpointPort, QuarantinePort, AuditPort, PiiHasherPort, InputFilterPort.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `20`

\newpage

<div style="page-break-before: always;"></div>

## 13e-operational-ports-domain — Domain Operational Ports

![13e-operational-ports-domain](architecture/png/13e-operational-ports-domain.png)

### Описание
Диаграмма «Domain Operational Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Independent protocol definitions for operational concerns (lock, checkpoint, observability, shutdown).. На схеме отражено примерно 8 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Operational Ports. Показательные узлы для быстрого чтения: fa:fa-lock LockPort, fa:fa-flag CheckpointPort, fa:fa-list LoggerPort, fa:fa-chart-line MetricsPort, fa:fa-wave-square TracingPort, fa:fa-bolt CircuitBreakerPort.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `8`

\newpage

<div style="page-break-before: always;"></div>

## 13f-operational-ports-infra — Infrastructure Operational Implementations

![13f-operational-ports-infra](architecture/png/13f-operational-ports-infra.png)

### Описание
Диаграмма «Infrastructure Operational Implementations» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Independent adapter implementations of operational ports.. На схеме отражено примерно 7 узлов, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Implementations. Показательные узлы для быстрого чтения: MemoryLock, LocalCheckpoint, UnifiedLogger, MetricsCollector, OpenTelemetryTracer, CircuitBreaker.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `7`

\newpage

<div style="page-break-before: always;"></div>

## 14-cli-interface-layer — CLI / Interface Layer

![14-cli-interface-layer](architecture/png/14-cli-interface-layer.png)

### Описание
Диаграмма «CLI / Interface Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: CLI commands, their routing, and interaction with composition.. На схеме отражено примерно 24 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: User, CLI Interface (Click), Run Commands, Health Commands, Data Commands, Maintenance Commands. Показательные узлы для быстрого чтения: Terminal, bioetl (main group), bioetl run --provider --entity --run-type --limit --resume --dry-run, bioetl run-composite ━━━━━━━━━━━━━━━━━ --config --run-type --resume, bioetl health ━━━━━━━━━━━━━━━━━ --provider Check API health, bioetl export ━━━━━━━━━━━━━━━━━ --table --format csv. Примечание: Decomposed into 14a-cli-commands, 14b-cli-routing.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `24`

\newpage

<div style="page-break-before: always;"></div>

## 14a-cli-commands — CLI: Command Structure

![14a-cli-commands](architecture/png/14a-cli-commands.png)

### Описание
Диаграмма «CLI: Command Structure» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Terminal entry point, main group, and all CLI commands with shutdown signal.. На схеме отражено примерно 12 узлов и 3 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: User, CLI Interface (Click), Run Commands, Health Commands, Data Commands, Maintenance Commands. Показательные узлы для быстрого чтения: Terminal, bioetl group, bioetl run, bioetl run-composite, bioetl health, bioetl export.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 14b-cli-routing — CLI: Routing to Composition & Application

![14b-cli-routing](architecture/png/14b-cli-routing.png)

### Описание
Диаграмма «CLI: Routing to Composition & Application» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: How CLI commands route through composition bootstrap to application services.. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Composition Layer, Application Layer. Показательные узлы для быстрого чтения: bioetl run, bioetl run-composite, bioetl health, bioetl export, bioetl quarantine, bioetl checkpoint.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`

\newpage

<div style="page-break-before: always;"></div>

## 15-batch-executor-internals — BatchExecutor Internal Architecture

![15-batch-executor-internals](architecture/png/15-batch-executor-internals.png)

### Описание
Диаграмма «BatchExecutor Internal Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: the composition of BatchExecutor and its helper components.. На схеме отражено примерно 15 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: BatchExecutor, Composed Helper Components, Data Flow Through Batch, TransformResult, Error Classification. Показательные узлы для быстрого чтения: BatchTracingManager -------- execution spans + start_batch_span() + end_span(), QuarantineManager -------- quarantine failed records + quarantine_record(), CheckpointManager -------- offset checkpoints + load/save/delete, Raw API Records (dict[str, Any]), Silver Records (Delta Lake), TransformResult silver_records + gold_records quarantined_count + errors.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `15`

\newpage

<div style="page-break-before: always;"></div>

## 16-transformer-hierarchy — Transformer Hierarchy

![16-transformer-hierarchy](architecture/png/16-transformer-hierarchy.png)

### Описание
Диаграмма «Transformer Hierarchy» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: the Template Method pattern and all provider-specific transformers.. На схеме отражено примерно 35 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Template Method Pattern, ChEMBL Transformers, Publication Transformers, UniProt Transformers, Other Transformers, Extractor Pattern. Показательные узлы для быстрого чтения: BaseChemblTransformer entity_class + primary_id_field _extract_business_data(), ActivityTransformer, PubMedPublicationTransformer XML parsing + extractor stack, UniProtProteinTransformer taxonomy/gene/feature extractors, IDMappingTransformer, PubChemCompoundTransformer. Примечание: Decomposed into 16a-transformer-base, 16b-transformer-pub-other.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `35`

\newpage

<div style="page-break-before: always;"></div>

## 16a-transformer-base — Base Transformer and ChEMBL Transformers

![16a-transformer-base](architecture/png/16a-transformer-base.png)

### Описание
Диаграмма «Base Transformer and ChEMBL Transformers» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Template Method base class, ChEMBL provider transformers, and extractor root.. На схеме отражено примерно 17 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Template Method Pattern, ChEMBL Transformers, Extractor Root. Показательные узлы для быстрого чтения: BaseTransformer ABC, BaseChemblTransformer, ActivityTransformer, AssayTransformer, ApprovedProductTransformer, MechanismTransformer.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `17`

\newpage

<div style="page-break-before: always;"></div>

## 16b-transformer-pub-other — Publication, UniProt, Other Transformers and Extractors

![16b-transformer-pub-other](architecture/png/16b-transformer-pub-other.png)

### Описание
Диаграмма «Publication, UniProt, Other Transformers and Extractors» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Provider-specific transformers and field extractor hierarchy.. На схеме отражено примерно 18 узлов и 3 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Publication Transformers, UniProt Transformers, Other Transformers, Field Extractors. Показательные узлы для быстрого чтения: BasePublicationTransformer, PubMedPublicationTransformer, CrossRefTransformer, OpenAlexTransformer, SemanticScholarTransformer, UniProtProteinTransformer.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `18`

\newpage

<div style="page-break-before: always;"></div>

## 17-security-pii-audit — Security, PII Hashing, and Audit Trail

![17-security-pii-audit](architecture/png/17-security-pii-audit.png)

### Описание
Диаграмма «Security, PII Hashing, and Audit Trail» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how PII is handled and audit trail is maintained.. На схеме отражено примерно 16 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Domain Types, PII Hashing Flow, Infrastructure: PII Hasher, Infrastructure: Audit, Usage in Transformers. Показательные узлы для быстрого чтения: PiiHasherPort (Protocol) -------- + hash(value: str) -> str, AuditPort (Protocol) -------- + log_write(entry) + get_entries(filters), AuditLayer -------- BRONZE / SILVER / GOLD, AuditOperation -------- WRITE / MERGE / APPEND DELETE / OVERWRITE, Raw PII Data (names, emails, affiliations), SHA256(lowercase(value) + salt).

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `16`

\newpage

<div style="page-break-before: always;"></div>

## 18-lock-checkpoint-shutdown — Locking, Checkpoint, and Graceful Shutdown

![18-lock-checkpoint-shutdown](architecture/png/18-lock-checkpoint-shutdown.png)

### Описание
Диаграмма «Locking, Checkpoint, and Graceful Shutdown» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: distributed safety mechanisms.. На схеме отражено примерно 22 узлов и 15 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Domain Lock Types, Application: LockCoordinator, Application: CheckpointManager, Application: Shutdown, Infrastructure: MemoryLock. Показательные узлы для быстрого чтения: LockPort (Protocol) acquire/release/heartbeat validate_owner + validate_token, CheckpointPort (Protocol) save/load/list/delete, ShutdownPort (Protocol), FencingToken sequence + key + owner_id + issued_at, LockNotHeldError, LockCoordinator lock + run_id + shutdown_signal acquire/release/validate. Примечание: Decomposed into 18a-lock-system, 18b-checkpoint-shutdown.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `22`

\newpage

<div style="page-break-before: always;"></div>

## 18a-lock-system — Lock System

![18a-lock-system](architecture/png/18a-lock-system.png)

### Описание
Диаграмма «Lock System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Lock ports, domain types, application manager, infrastructure implementation, and safety guard.. На схеме отражено примерно 8 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Port, Domain Lock Types, Application: LockCoordinator, Infrastructure: MemoryLock, Safety Guard. Показательные узлы для быстрого чтения: fa:fa-lock LockPort, FencingToken, LockNotHeldError, LockCoordinator, HeartbeatTask, MemoryLock.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `8`

\newpage

<div style="page-break-before: always;"></div>

## 18b-checkpoint-shutdown — Checkpoint and Shutdown System

![18b-checkpoint-shutdown](architecture/png/18b-checkpoint-shutdown.png)

### Описание
Диаграмма «Checkpoint and Shutdown System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Checkpoint and shutdown ports, managers, and pipeline lifecycle integration.. На схеме отражено примерно 14 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports, Application: CheckpointManager, Application: Shutdown, Infrastructure: LocalCheckpoint, Pipeline Lifecycle. Показательные узлы для быстрого чтения: fa:fa-flag CheckpointPort, fa:fa-power-off ShutdownPort, CheckpointManager, ShutdownSignal, ShutdownReason, LocalCheckpoint.

### Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `14`
