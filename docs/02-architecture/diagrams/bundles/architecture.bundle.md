# BioETL Architecture Diagrams Bundle

- Generated: 2026-04-13T12:35:16
- Diagram count: 57

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
- [12a-bootstrap-factories — Bootstrap: Registries, Public APIs, and Factory Seams](#12a-bootstrap-factories)
- [12b-bootstrap-wiring — Bootstrap: Runtime, Control-Plane, and Admin Wiring](#12b-bootstrap-wiring)
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
- [14b-cli-routing — CLI: Routing to Composition Boundary](#14b-cli-routing)
- [15-batch-executor-internals — BatchExecutor Internal Architecture](#15-batch-executor-internals)
- [16-transformer-hierarchy — Transformer Hierarchy](#16-transformer-hierarchy)
- [16a-transformer-base — Base Transformer and ChEMBL Transformers](#16a-transformer-base)
- [16b-transformer-pub-other — Publication, UniProt, Other Transformers and Blocks](#16b-transformer-pub-other)
- [17-security-pii-audit — Security, PII Hashing, and Audit Trail](#17-security-pii-audit)
- [18-lock-checkpoint-shutdown — Locking, Checkpoint, and Graceful Shutdown](#18-lock-checkpoint-shutdown)
- [18a-lock-system — Lock System](#18a-lock-system)
- [18b-checkpoint-shutdown — Checkpoint and Shutdown System](#18b-checkpoint-shutdown)
- [19-control-plane-artifacts — Control-Plane Artifacts and Traceability](#19-control-plane-artifacts)
- [20-data-traceability-runtime — Data Traceability Runtime Path](#20-data-traceability-runtime)
- [21-idempotent-processing-guards — Idempotent Processing Guards](#21-idempotent-processing-guards)
- [22-data-operations-observability — Data Operations Observability](#22-data-operations-observability)
- [23-reproducible-run-contract — Reproducible Run Contract](#23-reproducible-run-contract)

\\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-hexagonal

**High-Level Hexagonal Architecture**

![01-high-level-hexagonal](../architecture/svg/01-high-level-hexagonal.svg)

### Описание

Диаграмма «High-Level Hexagonal Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: the Ports & Adapters (Hexagonal) pattern across all layers.. Схема имеет плотность порядка 46 узлов и 29 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Systems, External APIs, interfaces layer, composition layer, application layer, domain layer (pure, no I/O). Показательные узлы для быстрого чтения: ChEMBL, PubMed, UniProt, PubChem, CrossRef, OpenAlex. Примечание: Decomposed into 01a, 01b, 01c sub-diagrams.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `46`

\\newpage

<div style="page-break-before: always;"></div>

## 01a-hexagonal-overview

**Hexagonal Overview**

![01a-hexagonal-overview](../architecture/svg/01a-hexagonal-overview.svg)

### Описание

Диаграмма «Hexagonal Overview» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers 5 architectural layers, external systems, and main dependency directions.. Схема имеет плотность порядка 11 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI Commands (Click), Orchestration, Bootstrap / Assembly, Application Core, Port Protocols, Provider Adapters.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 01b-hexagonal-domain-app

**Hexagonal Domain and Application**

![01b-hexagonal-domain-app](../architecture/svg/01b-hexagonal-domain-app.svg)

### Описание

Диаграмма «Hexagonal Domain and Application» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers domain contracts and core application services that depend on them.. Схема имеет плотность порядка 13 узлов и 7 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Application Layer, Domain Layer. Показательные узлы для быстрого чтения: Core (Runner, Executor, Transformer, Writer), Services (DQ, Export, Health, Lifecycle), Composite Pipeline (Coordinator, Merger, FSM), Pipeline Transformers (per provider), PipelineObserver, Port Protocols.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 01c-hexagonal-infra-comp

**Hexagonal Infrastructure and Composition**

![01c-hexagonal-infra-comp](../architecture/svg/01c-hexagonal-infra-comp.svg)

### Описание

Диаграмма «Hexagonal Infrastructure and Composition» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers infrastructure adapters and composition-root wiring points.. Схема имеет плотность порядка 14 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Composition Layer, Infrastructure Layer, Domain Layer. Показательные узлы для быстрого чтения: Bootstrap / Assembly, Factories, Provider Registry, Runtime Builders, HTTP Adapters, Storage.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 01d-hexagonal-overview-rounded

**Hexagonal Overview (Rounded Nodes)**

![01d-hexagonal-overview-rounded](../architecture/svg/01d-hexagonal-overview-rounded.svg)

### Описание

Диаграмма «Hexagonal Overview (Rounded Nodes)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers 5 architectural layers, external systems, and main dependency directions.. Схема имеет плотность порядка 11 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI Commands (Click), Orchestration, Bootstrap / Assembly, Application Core, Port Protocols, Provider Adapters.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-01`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 02-layer-dependency-matrix

**Layer Dependency Matrix (ARCH-001)**

![02-layer-dependency-matrix](../architecture/svg/02-layer-dependency-matrix.svg)

### Описание

Диаграмма «Layer Dependency Matrix (ARCH-001)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Enforced import boundaries between architectural layers.. Схема имеет плотность порядка 5 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Legend, Architectural Layers. Показательные узлы для быстрого чтения: ✅ Allowed, ❌ Forbidden, domain (pure business logic, no I/O, no frameworks), application (use cases, orchestration, transformers), infrastructure (adapters, storage, observability), composition (DI wiring, factories, bootstrap).

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 03-medallion-data-flow

**Medallion Architecture Data Flow (Bronze → Silver → Gold)**

![03-medallion-data-flow](../architecture/svg/03-medallion-data-flow.svg)

### Описание

Диаграмма «Medallion Architecture Data Flow (Bronze → Silver → Gold)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how data flows through the three medallion layers.. Схема имеет плотность порядка 36 узлов и 31 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Data Sources, Data Ingestion, Bronze Layer (Raw), Transformation, Silver Layer (Normalized), Gold Transformation. Показательные узлы для быстрого чтения: Semantic Scholar API, DataSourcePort fetch() / fetch_filtered(), RateLimiter (TokenBucket), CircuitBreaker, Retry Logic, BronzeWriter. Примечание: Canonical medallion flow — at threshold boundary.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `36`

\\newpage

<div style="page-break-before: always;"></div>

## 03a-medallion-layers-overview

**Medallion Layers Overview**

![03a-medallion-layers-overview](../architecture/svg/03a-medallion-layers-overview.svg)

### Описание

Диаграмма «Medallion Layers Overview» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Compact decomposition view for 03-medallion-data-flow.mmd (layer-level semantics). Схема имеет плотность порядка 12 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Ingestion, Processing, Serving. Показательные узлы для быстрого чтения: Provider APIs, Bronze Layer\\nRaw JSON, Normalize + Validate, Silver Layer\\nDelta Tables, DQ Checks, Quarantine. Связанный ADR: ADR-002, ADR-040.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`
- ADR: `ADR-002, ADR-040`

\\newpage

<div style="page-break-before: always;"></div>

## 04-pipeline-execution-flow

**Pipeline Execution Lifecycle**

![04-pipeline-execution-flow](../architecture/svg/04-pipeline-execution-flow.svg)

### Описание

Диаграмма «Pipeline Execution Lifecycle» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Sequence of phases in a single pipeline run.. Схема имеет плотность порядка 12 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 05-provider-adapter-hierarchy

**Provider Adapter Hierarchy**

![05-provider-adapter-hierarchy](../architecture/svg/05-provider-adapter-hierarchy.svg)

### Описание

Диаграмма «Provider Adapter Hierarchy» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how each provider adapter inherits from base classes and implements DataSourcePort.. Схема имеет плотность порядка 27 узлов и 24 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Mixins, Base Adapters, ChEMBL, PubMed, UniProt. Показательные узлы для быстрого чтения: DataSourcePort (Protocol), HealthCheckPort (Protocol), HealthCheckMixin, HealthCheckProviderMixin, NotSupportedMultiFilterMixin, DelegatingFallbackMixin. Примечание: Decomposed into 05a, 05b sub-diagrams.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `27`

\\newpage

<div style="page-break-before: always;"></div>

## 05a-adapter-hierarchy-base

**Adapter Hierarchy: Base Types**

![05a-adapter-hierarchy-base](../architecture/svg/05a-adapter-hierarchy-base.svg)

### Описание

Диаграмма «Adapter Hierarchy: Base Types» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers core ports, base adapters, reusable mixins, and adapter decorators.. Схема имеет плотность порядка 12 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, HealthCheckPort, HealthCheckProviderMixin, NotSupportedMultiFilterMixin, FilterableStubMixin, PaginatedFetcherMixin.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 05b-adapter-hierarchy-providers

**Adapter Hierarchy: Provider Implementations**

![05b-adapter-hierarchy-providers](../architecture/svg/05b-adapter-hierarchy-providers.svg)

### Описание

Диаграмма «Adapter Hierarchy: Provider Implementations» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers concrete provider adapters and provider-specific mixins.. Схема имеет плотность порядка 15 узлов и 12 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Infrastructure Layer. Показательные узлы для быстрого чтения: BaseHttpAdapter, BaseSyncAdapter, ChemblAdapter, PubMedAdapter, UniProtAdapter, CrossRefAdapter.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 06-storage-layer

**Storage Layer Components**

![06-storage-layer](../architecture/svg/06-storage-layer.svg)

### Описание

Диаграмма «Storage Layer Components» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers, metadata sidecar zones, Delta Lake, and validation.. Схема имеет плотность порядка 23 узлов и 27 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Port, Storage Writers, Bronze Storage, Silver Storage, Gold Storage, Delta Reader. Показательные узлы для быстрого чтения: StoragePort (Protocol), AtomicWriteGroup ━━━━━━━━━━━━━━━━━ Atomic multi-file writes with rollback, ArrowDataConverter (records → PyArrow), RetentionPolicy (vacuum/retention), MetadataWriter write_bronze / write_silver / write_gold, CsvExporter (Delta → CSV export). Примечание: Decomposed into 06a-storage-writers, 06b-storage-support.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-19`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 06a-storage-writers

**Storage Writers**

![06a-storage-writers](../architecture/svg/06a-storage-writers.svg)

### Описание

Диаграмма «Storage Writers» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers with Delta Lake base class, port contract, and file system layout.. Схема имеет плотность порядка 10 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Port, Bronze Storage, Silver Storage, Gold Storage, Delta Reader, File System Layout. Показательные узлы для быстрого чтения: StoragePort (Protocol), BronzeWriter write_bronze() / aclose(), AtomicWriteGroup atomic multi-file writes, BaseDeltaWriter get_table_path() / clear(), SilverWriter write_silver() / merge_silver(), GoldWriter write_gold() / clear_gold().

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 06b-storage-support

**Storage Support Components**

![06b-storage-support](../architecture/svg/06b-storage-support.svg)

### Описание

Диаграмма «Storage Support Components» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Support utilities, metadata write-preparation zones, validators, and metadata builders for the storage layer.. Схема имеет плотность порядка 14 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Support Components, Validation, Metadata Builders. Показательные узлы для быстрого чтения: ArrowDataConverter records → PyArrow, RetentionPolicy vacuum / retention, MetadataWriter layer-specific metadata writes, metadata_writer_operations target + YAML + retry telemetry, CsvExporter Delta → CSV export, DQReportWriter DQ reports JSON.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-19`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 07-dq-system

**Data Quality (DQ) System**

![07-dq-system](../architecture/svg/07-dq-system.svg)

### Описание

Диаграмма «Data Quality (DQ) System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: DQ monitoring, analysis, and reporting across all medallion layers.. Схема имеет плотность порядка 22 узлов и 24 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Application Services, Application DQ Analysis, Pipeline Integration, Domain Value Objects, Infrastructure Implementations. Показательные узлы для быстрого чтения: DQMonitorPort, BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort, DataQualityService -------- + evaluate(context, executor). Примечание: Decomposed into 07a-dq-analysis, 07b-dq-pipeline.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `22`

\\newpage

<div style="page-break-before: always;"></div>

## 07a-dq-analysis

**DQ Analysis Services**

![07a-dq-analysis](../architecture/svg/07a-dq-analysis.svg)

### Описание

Диаграмма «DQ Analysis Services» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Domain ports, application services, analyzers, and anomaly detection for Data Quality.. Схема имеет плотность порядка 12 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Application Services, DQ Analyzers, Anomaly Detection. Показательные узлы для быстрого чтения: DQMonitorPort, BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort, DataQualityService evaluate(context, executor).

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 07b-dq-pipeline

**DQ Pipeline Integration**

![07b-dq-pipeline](../architecture/svg/07b-dq-pipeline.svg)

### Описание

Диаграмма «DQ Pipeline Integration» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Pipeline DQ checks, domain value objects, and infrastructure config/report writers.. Схема имеет плотность порядка 10 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Pipeline Integration, Domain Value Objects, Infrastructure Implementations. Показательные узлы для быстрого чтения: BatchTransformer \_check_dq_thresholds(), QuarantineManager quarantines failed records, ErrorClassifier recoverable vs fatal, DQMetrics null_rate / duplicate_rate, DQResult passed / error_rate, DQReport layer / table_name / results.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 08-composite-pipeline

**Composite Pipeline Architecture**

![08-composite-pipeline](../architecture/svg/08-composite-pipeline.svg)

### Описание

Диаграмма «Composite Pipeline Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: seed → dependencies → enrichers (parallel) → merge flow.. Схема имеет плотность порядка 33 узлов и 34 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Composite Configuration, CompositePipelineRunner, State Machine, Execution Components, Dependencies (Sequential), Enrichers (Parallel Fan-Out). Показательные узлы для быстрого чтения: CompositeConfig, SeedConfig, DependencyConfig, EnricherConfig, MergeConfig, Config overview seed + dependencies enrichers + merge. Примечание: Decomposed into 08a-composite-config, 08b-composite-execution.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `33`

\\newpage

<div style="page-break-before: always;"></div>

## 08a-composite-config

**Composite Pipeline Configuration & FSM**

![08a-composite-config](../architecture/svg/08a-composite-config.svg)

### Описание

Диаграмма «Composite Pipeline Configuration & FSM» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Config hierarchy (CompositeConfig → sub-configs) and execution state machine.. Схема имеет плотность порядка 13 узлов и 13 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Composite Configuration, State Machine. Показательные узлы для быстрого чтения: CompositeConfig name / seed / deps / enrichers / merge, SeedConfig, DependencyConfig, EnricherConfig, MergeConfig, Config Details: seed → deps → enrichers → merge.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 08b-composite-execution

**Composite Pipeline Execution**

![08b-composite-execution](../architecture/svg/08b-composite-execution.svg)

### Описание

Диаграмма «Composite Pipeline Execution» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Runner orchestration: seed → deps → enrichers (parallel) → merge, with checkpointing and cross-validation.. Схема имеет плотность порядка 20 узлов и 20 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: CompositePipelineRunner, Preflight, Execution Components, Dependencies (Sequential), Enrichers (Parallel Fan-Out), Merge Phase. Показательные узлы для быстрого чтения: CompositePipelineRunner orchestrates full execution, PreflightValidator, Seed Pipeline, DependencyCoordinator, Dependency 1, EnrichmentCoordinator.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\\newpage

<div style="page-break-before: always;"></div>

## 09-observability-stack

**Observability Stack**

![09-observability-stack](../architecture/svg/09-observability-stack.svg)

### Описание

Диаграмма «Observability Stack» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Logging, Metrics, Tracing architecture.. Схема имеет плотность порядка 24 узлов и 13 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Application Emission, Composition-Owned Seams, Infrastructure: Logging, Infrastructure: Metrics, Infrastructure: Tracing. Показательные узлы для быстрого чтения: LoggerPort (Protocol) bind + info/warn/error/debug/exception, MetricsPort (Protocol) observe_histogram + increment_counter set_gauge + close, TracingPort (Protocol) get_tracer + close, DQMonitorPort (Protocol) add_metric + check_quality update_baseline, PipelineObserver canonical lifecycle emitter ordinary runs, PipelineMetricsRecorder pipeline-scoped metric vocabulary. Примечание: Decomposed into 09a-observability-app, 09b-observability-infra.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-04-12`
- Узлы (metadata): `24`

\\newpage

<div style="page-break-before: always;"></div>

## 09a-observability-app

**Observability: Application Layer**

![09a-observability-app](../architecture/svg/09a-observability-app.svg)

### Описание

Диаграмма «Observability: Application Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Application-level observability: ports, pipeline observer, batch metrics, adapter metrics.. Схема имеет плотность порядка 10 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Application Observability. Показательные узлы для быстрого чтения: LoggerPort (Protocol), MetricsPort (Protocol), TracingPort (Protocol), DQMonitorPort (Protocol), PipelineObserver canonical lifecycle emitter, PipelineMetricsRecorder.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-04-12`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 09b-observability-infra

**Observability: Infrastructure Layer**

![09b-observability-infra](../architecture/svg/09b-observability-infra.svg)

### Описание

Диаграмма «Observability: Infrastructure Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Infrastructure implementations: logging, metrics, tracing, anomaly detection, external systems.. Схема имеет плотность порядка 12 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Infrastructure: Logging, Infrastructure: Metrics, Infrastructure: Tracing, Infrastructure: Anomaly Detection, External Systems. Показательные узлы для быстрого чтения: UnifiedLogger (impl LoggerPort), NoOpLogger (compat fallback), PrometheusMetrics (impl MetricsPort), MetricsServerAdapter (MetricsServerPort seam), MetricsPublisherAdapter (MetricsPublisherPort seam), MetricsCollector (compat convenience wrapper).

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-04-12`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 10-resilience-patterns

**Resilience Patterns**

![10-resilience-patterns](../architecture/svg/10-resilience-patterns.svg)

### Описание

Диаграмма «Resilience Patterns» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Circuit Breaker, Rate Limiter, Retry, Health Check patterns.. Схема имеет плотность порядка 15 узлов и 13 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Circuit Breaker Pattern, State Machine, Rate Limiter (Token Bucket), Provider Rate Limits, Retry Logic. Показательные узлы для быстрого чтения: CircuitBreakerPort (Protocol) -------- + get_state() + call(fn), RateLimiterPort (Protocol) -------- + acquire(tokens) + try_acquire(), HealthCheckPort (Protocol) -------- + check_health(), CircuitBreaker -------- provider failure_threshold recovery_timeout, CLOSED (normal operation), OPEN (fail fast).

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 11-configuration-system

**Configuration System**

![11-configuration-system](../architecture/svg/11-configuration-system.svg)

### Описание

Диаграмма «Configuration System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how YAML configs are loaded, validated, and published as effective-config and manifest provenance artifacts.. Схема имеет плотность порядка 31 узлов и 31 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic), Domain Configuration, Composite Domain Config, Application Config. Показательные узлы для быстрого чтения: configs/base/*.yaml pipeline and quality defaults, configs/providers/*.yaml source plus provider defaults, configs/entities/*/*.yaml unified entity configs, configs/composites/\*.yaml composite configs, PipelineConfigLoader load(path) -> PipelineConfig, DQConfigLoader load(path) -> DQConfig. Примечание: Decomposed into 11a-config-loading, 11b-config-domain.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `31`

\\newpage

<div style="page-break-before: always;"></div>

## 11a-config-loading

**Configuration: Loading Pipeline**

![11a-config-loading](../architecture/svg/11a-config-loading.svg)

### Описание

Диаграмма «Configuration: Loading Pipeline» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: YAML files, config loaders, and infrastructure schemas (Pydantic validation).. Схема имеет плотность порядка 11 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic). Показательные узлы для быстрого чтения: configs/base/*.yaml, configs/providers/*.yaml, configs/entities/*/*.yaml, configs/composites/\*.yaml, BaseConfigLoader, PipelineConfigLoader.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 11b-config-domain

**Configuration: Domain & Application Config**

![11b-config-domain](../architecture/svg/11b-config-domain.svg)

### Описание

Диаграмма «Configuration: Domain & Application Config» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Domain config objects, composite config, application config, and infrastructure settings.. Схема имеет плотность порядка 16 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Infrastructure Schemas, Domain Configuration, Composite Domain Config, Application Config, Infrastructure Settings. Показательные узлы для быстрого чтения: ApiConfig, SourceConfig, CircuitBreakerConfig, PipelineContractPolicy, PipelineConfig, TableConfig.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 12-bootstrap-di-container

**Bootstrap / DI Container (Composition Root)**

![12-bootstrap-di-container](../architecture/svg/12-bootstrap-di-container.svg)

### Описание

Диаграмма «Bootstrap / DI Container (Composition Root)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: current public composition seams, runtime assembly, and control-plane artifact wiring.. Схема имеет плотность порядка 25 узлов и 39 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Public composition seams, Registries + factories, Runtime assembly path, Admin / support bootstrap, Created services + artifacts. Показательные узлы для быстрого чтения: Entry callers CLI + tests/scripts + programmatic integrations, composition.entrypoints broad retained facade, execution_api / services_api / resources_api narrow command-facing seams, composition.bootstrap lower-level runtime / cli seam, ProviderRegistry provider creators + source defaults, PipelineRegistry pipeline factory lookup. Примечание: Decomposed into 12a, 12b sub-diagrams; complements 19-control-plane-artifacts.mmd.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 12a-bootstrap-factories

**Bootstrap: Registries, Public APIs, and Factory Seams**

![12a-bootstrap-factories](../architecture/svg/12a-bootstrap-factories.svg)

### Описание

Диаграмма «Bootstrap: Registries, Public APIs, and Factory Seams» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Focuses on current entrypoint/bootstrap surfaces, registries, provider wiring, and canonical factory seams.. Схема имеет плотность порядка 11 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Registries + factories. Показательные узлы для быстрого чтения: composition.entrypoints run/build + service getters, composition.bootstrap lower-level seam, ProviderRegistry, PipelineRegistry, DataSourceFactory, GenericPipelineFactory / RunnerFactory.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-24`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 12b-bootstrap-wiring

**Bootstrap: Runtime, Control-Plane, and Admin Wiring**

![12b-bootstrap-wiring](../architecture/svg/12b-bootstrap-wiring.svg)

### Описание

Диаграмма «Bootstrap: Runtime, Control-Plane, and Admin Wiring» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers how current entrypoints/bootstrap seams expose runtime, control-plane, and admin assembly outputs.. Схема имеет плотность порядка 23 узлов и 31 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Public composition APIs, Composition bootstrap, Infrastructure collaborators, Created services, Control-plane artifacts. Показательные узлы для быстрого чтения: composition.entrypoints, execution_api / services_api / resources_api, composition.bootstrap lower-level seam, bootstrap_pipeline_runner, bootstrap_pipeline_runner_service, build_pipeline_runner.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 13-port-protocol-contracts

**Port/Protocol Contracts (Full Map)**

![13-port-protocol-contracts](../architecture/svg/13-port-protocol-contracts.svg)

### Описание

Диаграмма «Port/Protocol Contracts (Full Map)» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Domain ports mapped to their current application consumers and infrastructure adapters.. Схема имеет плотность порядка 48 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain ports (Protocols), Application consumers, Infrastructure adapters. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, CompositeCheckpointPort. Примечание: Decomposed into 13a, 13b, 13c, 13d, 13e, 13f sub-diagrams.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `48`

\\newpage

<div style="page-break-before: always;"></div>

## 13a-data-storage-ports

**DataSource and Storage Ports**

![13a-data-storage-ports](../architecture/svg/13a-data-storage-ports.svg)

### Описание

Диаграмма «DataSource and Storage Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: All data acquisition and storage ports.. Схема имеет плотность порядка 20 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Implementations. Показательные узлы для быстрого чтения: fa:fa-plug DataSourcePort, fa:fa-filter FilterableDataSourcePort, fa:fa-database StoragePort, fa:fa-book-open DeltaReaderPort, fa:fa-file-import InputFilterPort, ChemblAdapter.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\\newpage

<div style="page-break-before: always;"></div>

## 13a-port-contracts-data-sources

**Port Contracts: Data Sources**

![13a-port-contracts-data-sources](../architecture/svg/13a-port-contracts-data-sources.svg)

### Описание

Диаграмма «Port Contracts: Data Sources» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers DataSourcePort and FilterableDataSourcePort implementations per provider.. Схема имеет плотность порядка 9 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, ChemblAdapter.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-25`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 13b-operational-ports

**Operational and Observability Ports**

![13b-operational-ports](../architecture/svg/13b-operational-ports.svg)

### Описание

Диаграмма «Operational and Observability Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Monitoring, logging, and operational control ports.. Схема имеет плотность порядка 25 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Implementations. Показательные узлы для быстрого чтения: fa:fa-lock LockPort, fa:fa-flag CheckpointPort, fa:fa-list LoggerPort, fa:fa-chart-line MetricsPort, fa:fa-wave-square TracingPort, fa:fa-bolt CircuitBreakerPort. Примечание: Decomposed into 13e-operational-ports-domain, 13f-operational-ports-infra.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 13b-port-contracts-storage

**Port Contracts: Storage**

![13b-port-contracts-storage](../architecture/svg/13b-port-contracts-storage.svg)

### Описание

Диаграмма «Port Contracts: Storage» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers StoragePort, DeltaReaderPort, and layer-specific MetadataWriterPort implementations.. Схема имеет плотность порядка 9 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: StoragePort, DeltaReaderPort, MetadataWriterPort write_bronze / write_silver / write_gold, BronzeWriter, DeltaReader, MetadataWriter atomic metadata sidecars.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-19`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 13c-port-contracts-observability

**Port Contracts: Observability and Resilience**

![13c-port-contracts-observability](../architecture/svg/13c-port-contracts-observability.svg)

### Описание

Диаграмма «Port Contracts: Observability and Resilience» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Covers Logger/Metrics/Tracing ports plus resilience control ports.. Схема имеет плотность порядка 18 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer, Domain NoOp Compatibility, Infrastructure Layer. Показательные узлы для быстрого чтения: LoggerPort, MetricsPort, TracingPort, DQMonitorPort, AuditPort, CircuitBreakerPort.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-04-12`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 13c-validation-dq-ports

**Validation and Data Quality Ports**

![13c-validation-dq-ports](../architecture/svg/13c-validation-dq-ports.svg)

### Описание

Диаграмма «Validation and Data Quality Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Ports for ensuring data correctness and quality reporting.. Схема имеет плотность порядка 20 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Infrastructure, Application. Показательные узлы для быстрого чтения: SilverValidatorPort, GoldValidatorPort, BronzeDQ AnalyzerPort, SilverDQ AnalyzerPort, GoldDQ AnalyzerPort, DQReportWriterPort.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `20`

\\newpage

<div style="page-break-before: always;"></div>

## 13d-port-contracts-services

**Port Contracts: Services and Controls**

![13d-port-contracts-services](../architecture/svg/13d-port-contracts-services.svg)

### Описание

Диаграмма «Port Contracts: Services and Controls» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Control-plane, checkpoint, and DQ service ports with their current consumers and adapters.. Схема имеет плотность порядка 22 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Application Layer. Показательные узлы для быстрого чтения: LockPort, CheckpointPort, CompositeCheckpointPort, QuarantinePort, AuditPort, PiiHasherPort.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `22`

\\newpage

<div style="page-break-before: always;"></div>

## 13e-operational-ports-domain

**Domain Operational Ports**

![13e-operational-ports-domain](../architecture/svg/13e-operational-ports-domain.svg)

### Описание

Диаграмма «Domain Operational Ports» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Independent protocol definitions for operational concerns, including control-plane traceability ports.. Схема имеет плотность порядка 11 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Operational Ports. Показательные узлы для быстрого чтения: fa:fa-lock LockPort, fa:fa-flag CheckpointPort, fa:fa-layer-group CompositeCheckpointPort, fa:fa-list LoggerPort, fa:fa-chart-line MetricsPort, fa:fa-wave-square TracingPort.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 13f-operational-ports-infra

**Infrastructure Operational Implementations**

![13f-operational-ports-infra](../architecture/svg/13f-operational-ports-infra.svg)

### Описание

Диаграмма «Infrastructure Operational Implementations» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Current adapter implementations of operational and control-plane traceability ports.. Схема имеет плотность порядка 10 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Infrastructure Implementations. Показательные узлы для быстрого чтения: MemoryLock, LocalCheckpoint, UnifiedLogger, MetricsCollector, OpenTelemetryTracer, CircuitBreaker.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 14-cli-interface-layer

**CLI / Interface Layer**

![14-cli-interface-layer](../architecture/svg/14-cli-interface-layer.svg)

### Описание

Диаграмма «CLI / Interface Layer» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: current CLI routing through registry helpers, narrow composition APIs, and inspection/admin services.. Схема имеет плотность порядка 18 узлов и 23 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: interfaces/cli, composition boundary, Created runtime services. Показательные узлы для быстрого чтения: Terminal user, cli.main Click group, registry_helpers fresh explicit PipelineRegistry, run / run-all, run-composite, run-manifest / lineage. Примечание: Decomposed into 14a-cli-commands, 14b-cli-routing.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 14a-cli-commands

**CLI: Command Structure**

![14a-cli-commands](../architecture/svg/14a-cli-commands.svg)

### Описание

Диаграмма «CLI: Command Structure» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Terminal entrypoint, main group, and the current command families registered in cli.main.. Схема имеет плотность порядка 13 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: cli.main command groups. Показательные узлы для быстрого чтения: Terminal, bioetl group, run / run-all, run-composite, run-manifest / lineage, checkpoint / config / dq health / export / quarantine / lock.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 14b-cli-routing

**CLI: Routing to Composition Boundary**

![14b-cli-routing](../architecture/svg/14b-cli-routing.svg)

### Описание

Диаграмма «CLI: Routing to Composition Boundary» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how command families route through registry helpers and narrow composition APIs, while entrypoints remains a retained broad seam.. Схема имеет плотность порядка 15 узлов и 17 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: interfaces/cli helpers, composition boundary, Runtime services. Показательные узлы для быстрого чтения: run / run-all, run-composite, run-manifest / lineage, health / export / quarantine checkpoint / config / dq / lock / maintenance, registry_helpers, execution_api.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 15-batch-executor-internals

**BatchExecutor Internal Architecture**

![15-batch-executor-internals](../architecture/svg/15-batch-executor-internals.svg)

### Описание

Диаграмма «BatchExecutor Internal Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Component / Service». В комментариях исходника зафиксирован фокус диаграммы: the current decomposition of BatchExecutor runtime orchestration.. Схема имеет плотность порядка 16 узлов и 25 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: BatchExecutor Shell, Run Orchestration, Processing And State Contracts, BatchProcessingService Internals. Показательные узлы для быстрого чтения: BatchTransformer -------- transform_batch() quarantine + DQ thresholds, BatchWriter -------- write_bronze/silver/gold lock-safe validation path, QuarantineManagerService -------- quarantine_record() quarantine_records().

### Метаданные

- Тип: `flowchart`
- Уровень: `Component / Service`
- Дата: `2026-03-24`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 16-transformer-hierarchy

**Transformer Hierarchy**

![16-transformer-hierarchy](../architecture/svg/16-transformer-hierarchy.svg)

### Описание

Диаграмма «Transformer Hierarchy» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: the Template Method pattern, declarative publication blocks, and provider-specific helper seams.. Схема имеет плотность порядка 27 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Template Method Pattern, ChEMBL Transformers, Publication Transformers, UniProt Transformers, Other Transformers, Block + Helper Strategy. Показательные узлы для быстрого чтения: BaseChemblTransformer entity_class + primary_id_field \_extract_business_data(), ActivityTransformer, PubMedPublicationTransformer cached XML root + extraction_blocks, UniProtProteinTransformer taxonomy/gene/feature extractors, IDMappingTransformer, PubChemCompoundTransformer. Примечание: Decomposed into 16a-transformer-base, 16b-transformer-pub-other.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-19`
- Узлы (metadata): `27`

\\newpage

<div style="page-break-before: always;"></div>

## 16a-transformer-base

**Base Transformer and ChEMBL Transformers**

![16a-transformer-base](../architecture/svg/16a-transformer-base.svg)

### Описание

Диаграмма «Base Transformer and ChEMBL Transformers» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Template Method base class, ChEMBL provider transformers, and extractor root.. Схема имеет плотность порядка 17 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Template Method Pattern, ChEMBL Transformers, Extractor Root. Показательные узлы для быстрого чтения: BaseTransformer ABC, BaseChemblTransformer, ActivityTransformer, AssayTransformer, ApprovedProductTransformer, MechanismTransformer.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-27`
- Узлы (metadata): `17`

\\newpage

<div style="page-break-before: always;"></div>

## 16b-transformer-pub-other

**Publication, UniProt, Other Transformers and Blocks**

![16b-transformer-pub-other](../architecture/svg/16b-transformer-pub-other.svg)

### Описание

Диаграмма «Publication, UniProt, Other Transformers and Blocks» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Provider-specific transformers, declarative PubMed blocks, and helper extractor seams.. Схема имеет плотность порядка 16 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Publication Transformers, UniProt Transformers, Other Transformers, Blocks + Helper Extractors. Показательные узлы для быстрого чтения: BasePublicationTransformer, PubMedPublicationTransformer, CrossRefPublicationTransformer, OpenAlexPublicationTransformer, SemanticScholarPublicationTransformer, UniProtProteinTransformer.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-19`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 17-security-pii-audit

**Security, PII Hashing, and Audit Trail**

![17-security-pii-audit](../architecture/svg/17-security-pii-audit.svg)

### Описание

Диаграмма «Security, PII Hashing, and Audit Trail» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how PII is handled and audit trail is maintained.. Схема имеет плотность порядка 16 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Domain Types, PII Hashing Flow, Infrastructure: PII Hasher, Infrastructure: Audit, Usage in Transformers. Показательные узлы для быстрого чтения: PiiHasherPort (Protocol) -------- + hash(value: str) -> str, AuditPort (Protocol) -------- + log_write(entry) + get_entries(filters), AuditLayer -------- BRONZE / SILVER / GOLD, AuditOperation -------- WRITE / MERGE / APPEND DELETE / OVERWRITE, Raw PII Data (names, emails, affiliations), SHA256(lowercase(value) + salt).

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-02-24`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 18-lock-checkpoint-shutdown

**Locking, Checkpoint, and Graceful Shutdown**

![18-lock-checkpoint-shutdown](../architecture/svg/18-lock-checkpoint-shutdown.svg)

### Описание

Диаграмма «Locking, Checkpoint, and Graceful Shutdown» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Distinguishes general pipeline lifecycle from the newer composite checkpoint facade and resume semantics.. Схема имеет плотность порядка 22 узлов и 21 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports, Domain Lock Types, Application: LockCoordinator, Application: Checkpoint Services, Application: Shutdown, Infrastructure: MemoryLock. Показательные узлы для быстрого чтения: LockPort (Protocol) acquire/release/heartbeat validate_owner + validate_token, CheckpointPort (Protocol) save/load/list/delete, CompositeCheckpointPort (composite phase checkpoints), ShutdownPort (Protocol), FencingToken + LockNotHeldError, LockCoordinator lock + run_id + shutdown_signal acquire/release/validate. Примечание: Decomposed into 18a-lock-system, 18b-checkpoint-shutdown.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `22`

\\newpage

<div style="page-break-before: always;"></div>

## 18a-lock-system

**Lock System**

![18a-lock-system](../architecture/svg/18a-lock-system.svg)

### Описание

Диаграмма «Lock System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Distinguishes the general LockCoordinator path from the composite runner's direct LockPort path.. Схема имеет плотность порядка 10 узлов и 7 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain lock contracts, General pipeline lifecycle, Composite runtime path, Infrastructure. Показательные узлы для быстрого чтения: LockPort, FencingToken, LockNotHeldError, LockCoordinator, HeartbeatTask, CompositePipelineRunnerService.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-16`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 18b-checkpoint-shutdown

**Checkpoint and Shutdown System**

![18b-checkpoint-shutdown](../architecture/svg/18b-checkpoint-shutdown.svg)

### Описание

Диаграмма «Checkpoint and Shutdown System» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Separates general checkpoint/shutdown services from the composite checkpoint facade and resume helpers.. Схема имеет плотность порядка 15 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain ports, Application services, Infrastructure, Lifecycle integration. Показательные узлы для быстрого чтения: CheckpointPort, CompositeCheckpointPort, ShutdownPort, CheckpointManagerService, CompositeCheckpointService thin facade, CompositeCheckpointLoadService.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-03-28`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 19-control-plane-artifacts

**Control-Plane Artifacts and Traceability**

![19-control-plane-artifacts](../architecture/svg/19-control-plane-artifacts.svg)

### Описание

Диаграмма «Control-Plane Artifacts and Traceability» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: how runtime assembly publishes immutable provenance artifacts and resumes composite runs from checkpoint snapshot + ledger suffix replay.. Схема имеет плотность порядка 24 узлов и 34 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Runtime descriptors, Composition runtime builders, Application services, Domain ports + replay model, Infrastructure stores, Published artifacts. Показательные узлы для быстрого чтения: build_pipeline_runner / CLI run, run-manifest / lineage / inspection CLI, PipelineRunContext launch descriptor, PipelineContext in-run processing context, create_run_manifest_with_effective_config publish manifest + effective config, attach_control_plane_collaborators bind manifest / ledger / lineage. Примечание: Complements 12-bootstrap-di-container, 18-lock-checkpoint-shutdown, 23-reproducible-run-contract, and ADR-044.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата: `2026-04-02`
- Узлы (metadata): `24`

\\newpage

<div style="page-break-before: always;"></div>

## 20-data-traceability-runtime

**Data Traceability Runtime Path**

![20-data-traceability-runtime](../architecture/svg/20-data-traceability-runtime.svg)

### Описание

Диаграмма «Data Traceability Runtime Path» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Runtime». В комментариях исходника зафиксирован фокус диаграммы: how one pipeline run becomes inspectable through manifest, ledger, lineage, and artifact identity anchors.. Схема имеет плотность порядка 20 узлов и 31 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Composition runtime assembly, Application control-plane services, Infrastructure stores, Execution + publication, Traceability anchors. Показательные узлы для быстрого чтения: CLI run / scheduler caller, run-manifest + lineage CLI, build_pipeline_runner, prepare_runner_inputs, create_run_manifest_with_effective_config, EffectiveConfigService. Примечание: Complements 19-control-plane-artifacts, 18-lock-checkpoint-shutdown, and 38-runtime-assembly-sequence. Связанный ADR: ADR-044.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Runtime`
- Дата: `2026-03-28`
- Узлы (metadata): `20`
- ADR: `ADR-044`

\\newpage

<div style="page-break-before: always;"></div>

## 21-idempotent-processing-guards

**Idempotent Processing Guards**

![21-idempotent-processing-guards](../architecture/svg/21-idempotent-processing-guards.svg)

### Описание

Диаграмма «Idempotent Processing Guards» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Runtime / Control Plane». В комментариях исходника зафиксирован фокус диаграммы: how locks, checkpoint identity, and publication guards make reruns/resume safe.. Схема имеет плотность порядка 10 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Примечание: Complements 18-lock-checkpoint-shutdown, 20-data-traceability-runtime, and ADR-014 deterministic writes.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Runtime / Control Plane`
- Дата: `2026-03-28`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 22-data-operations-observability

**Data Operations Observability**

![22-data-operations-observability](../architecture/svg/22-data-operations-observability.svg)

### Описание

Диаграмма «Data Operations Observability» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Runtime». В комментариях исходника зафиксирован фокус диаграммы: how logs, metrics, tracing, and control-plane signals stay correlated without high-cardinality metric labels.. Схема имеет плотность порядка 18 узлов и 19 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Runtime event producers, Application observability contracts, Infrastructure observability, Published signals, Monitoring and diagnosis. Показательные узлы для быстрого чтения: PipelineObserver, PipelineRunner / CompositeRunner, HTTP adapters + health checks, Manifest / ledger / lineage events, LoggerPort, MetricsPort. Примечание: Complements 09-observability-stack, 20-data-traceability-runtime, and observability.md.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Runtime`
- Дата: `2026-03-28`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 23-reproducible-run-contract

**Reproducible Run Contract**

![23-reproducible-run-contract](../architecture/svg/23-reproducible-run-contract.svg)

### Описание

Диаграмма «Reproducible Run Contract» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Control Plane». В комментариях исходника зафиксирован фокус диаграммы: how config resolution, runtime descriptors, and control-plane provenance define one replay/comparison identity.. Схема имеет плотность порядка 23 узлов и 35 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Configuration inputs, Resolution services, Runtime descriptors, Published reproducibility artifacts, Identity anchors, Replay / comparison consumers. Показательные узлы для быстрого чтения: Provider / entity / composite YAML, ConfigSourceRef[], Runtime overrides CLI + env + runtime, DQ contract refs + bundle versions, Config loaders + resolution policy, EffectiveConfigService. Примечание: Complements 11-configuration-system, 19-control-plane-artifacts, and config-runtime-artifacts.md.

### Метаданные

- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата: `2026-04-02`
- Узлы (metadata): `23`
