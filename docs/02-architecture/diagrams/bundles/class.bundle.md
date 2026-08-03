# BioETL Class Diagrams Bundle

- Generated: 2026-04-13T12:35:19
- Diagram count: 94

## Table of Contents

- [01-domain-ports — Class Diagram: Domain Port Protocols](#01-domain-ports)
- [01a-domain-ports-method-catalog — Class Diagram: Domain Port Method Catalog (L2)](#01a-domain-ports-method-catalog)
- [02-entities-aggregates — Class Diagram: Entities & Aggregates](#02-entities-aggregates)
- [03-value-objects — Class Diagram: Value Objects](#03-value-objects)
- [04-types-enums — Class Diagram: Types & Enums](#04-types-enums)
- [05-exceptions — Class Diagram: Exception Hierarchy](#05-exceptions)
- [06-config-classes — Class Diagram: Configuration Classes](#06-config-classes)
- [07-application-core-services-frontmatter-sandbox — 07 Application Core Services Frontmatter Sandbox](#07-application-core-services-frontmatter-sandbox)
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
- [15-extractors — Class Diagram: Field Extractors and Publication Blocks](#15-extractors)
- [16-factories-bootstrap — Class Diagram: Factories & Bootstrap](#16-factories-bootstrap)
- [90-pkg-application-composite-checkpoint — Package Family: application/composite/checkpoint](#90-pkg-application-composite-checkpoint)
- [90-pkg-application-composite-runner-pkg-part1 — Package Family: application/composite/runner_pkg (Part 1/2)](#90-pkg-application-composite-runner-pkg-part1)
- [90-pkg-application-composite-runner-pkg-part2 — Package Family: application/composite/runner_pkg (Part 2/2)](#90-pkg-application-composite-runner-pkg-part2)
- [90-pkg-application-core-base-transformer — Package Family: application/core/base_transformer](#90-pkg-application-core-base-transformer)
- [90-pkg-application-core-batch-execution — Package Family: application/core/batch_execution](#90-pkg-application-core-batch-execution)
- [90-pkg-application-core-lifecycle — Package Family: application/core/lifecycle](#90-pkg-application-core-lifecycle)
- [90-pkg-application-core-postrun — Package Family: application/core/postrun](#90-pkg-application-core-postrun)
- [90-pkg-application-core-preflight — Package Family: application/core/preflight](#90-pkg-application-core-preflight)
- [90-pkg-application-observability — Package Family: application/observability](#90-pkg-application-observability)
- [90-pkg-application-pipelines-chembl — Package Family: application/pipelines/chembl](#90-pkg-application-pipelines-chembl)
- [90-pkg-application-pipelines-common — Package Family: application/pipelines/common](#90-pkg-application-pipelines-common)
- [90-pkg-application-pipelines-pubmed — Package Family: application/pipelines/pubmed](#90-pkg-application-pipelines-pubmed)
- [90-pkg-application-pipelines-uniprot-extractors — Package Family: application/pipelines/uniprot/extractors](#90-pkg-application-pipelines-uniprot-extractors)
- [90-pkg-application-pipelines-uniprot — Package Family: application/pipelines/uniprot](#90-pkg-application-pipelines-uniprot)
- [90-pkg-application-services-dq — Package Family: application/services/dq](#90-pkg-application-services-dq)
- [90-pkg-composition-bootstrap-runtime — Package Family: composition/bootstrap/runtime](#90-pkg-composition-bootstrap-runtime)
- [90-pkg-composition-factories-datasource — Package Family: composition/factories/datasource](#90-pkg-composition-factories-datasource)
- [90-pkg-composition-factories-services — Package Family: composition/factories/services](#90-pkg-composition-factories-services)
- [90-pkg-composition-factories-storage — Package Family: composition/factories/storage](#90-pkg-composition-factories-storage)
- [90-pkg-composition-providers — Package Family: composition/providers](#90-pkg-composition-providers)
- [90-pkg-composition-runtime-builders — Package Family: composition/runtime_builders](#90-pkg-composition-runtime-builders)
- [90-pkg-composition — Package Family: composition](#90-pkg-composition)
- [90-pkg-domain-aggregates — Package Family: domain/aggregates](#90-pkg-domain-aggregates)
- [90-pkg-domain-composite-part1 — Package Family: domain/composite (Part 1/2)](#90-pkg-domain-composite-part1)
- [90-pkg-domain-composite-part2 — Package Family: domain/composite (Part 2/2)](#90-pkg-domain-composite-part2)
- [90-pkg-domain-contracts-gold — Package Family: domain/contracts/gold](#90-pkg-domain-contracts-gold)
- [90-pkg-domain-control-plane — Package Family: domain/control_plane](#90-pkg-domain-control-plane)
- [90-pkg-domain-exceptions-infrastructure — Package Family: domain/exceptions/infrastructure](#90-pkg-domain-exceptions-infrastructure)
- [90-pkg-domain-exceptions-network — Package Family: domain/exceptions/network](#90-pkg-domain-exceptions-network)
- [90-pkg-domain-filtering — Package Family: domain/filtering](#90-pkg-domain-filtering)
- [90-pkg-domain-lineage — Package Family: domain/lineage](#90-pkg-domain-lineage)
- [90-pkg-domain-models — Package Family: domain/models](#90-pkg-domain-models)
- [90-pkg-domain-ports-config — Package Family: domain/ports/config](#90-pkg-domain-ports-config)
- [90-pkg-domain-ports-metadata — Package Family: domain/ports/metadata](#90-pkg-domain-ports-metadata)
- [90-pkg-domain-ports-noop — Package Family: domain/ports/noop](#90-pkg-domain-ports-noop)
- [90-pkg-domain-ports-observability — Package Family: domain/ports/observability](#90-pkg-domain-ports-observability)
- [90-pkg-domain-ports-quality — Package Family: domain/ports/quality](#90-pkg-domain-ports-quality)
- [90-pkg-domain-ports-runtime — Package Family: domain/ports/runtime](#90-pkg-domain-ports-runtime)
- [90-pkg-domain-ports-storage — Package Family: domain/ports/storage](#90-pkg-domain-ports-storage)
- [90-pkg-domain-schemas-chembl — Package Family: domain/schemas/chembl](#90-pkg-domain-schemas-chembl)
- [90-pkg-domain-schemas-pubchem — Package Family: domain/schemas/pubchem](#90-pkg-domain-schemas-pubchem)
- [90-pkg-domain-schemas-uniprot — Package Family: domain/schemas/uniprot](#90-pkg-domain-schemas-uniprot)
- [90-pkg-domain — Package Family: domain](#90-pkg-domain)
- [90-pkg-infrastructure-adapters-chembl-part1 — Package Family: infrastructure/adapters/chembl (Part 1/2)](#90-pkg-infrastructure-adapters-chembl-part1)
- [90-pkg-infrastructure-adapters-chembl-part2 — Package Family: infrastructure/adapters/chembl (Part 2/2)](#90-pkg-infrastructure-adapters-chembl-part2)
- [90-pkg-infrastructure-adapters-common — Package Family: infrastructure/adapters/common](#90-pkg-infrastructure-adapters-common)
- [90-pkg-infrastructure-adapters-crossref — Package Family: infrastructure/adapters/crossref](#90-pkg-infrastructure-adapters-crossref)
- [90-pkg-infrastructure-adapters-http — Package Family: infrastructure/adapters/http](#90-pkg-infrastructure-adapters-http)
- [90-pkg-infrastructure-adapters-openalex — Package Family: infrastructure/adapters/openalex](#90-pkg-infrastructure-adapters-openalex)
- [90-pkg-infrastructure-adapters-pubchem — Package Family: infrastructure/adapters/pubchem](#90-pkg-infrastructure-adapters-pubchem)
- [90-pkg-infrastructure-adapters-pubmed — Package Family: infrastructure/adapters/pubmed](#90-pkg-infrastructure-adapters-pubmed)
- [90-pkg-infrastructure-adapters-semanticscholar — Package Family: infrastructure/adapters/semanticscholar](#90-pkg-infrastructure-adapters-semanticscholar)
- [90-pkg-infrastructure-adapters-uniprot-part1 — Package Family: infrastructure/adapters/uniprot (Part 1/2)](#90-pkg-infrastructure-adapters-uniprot-part1)
- [90-pkg-infrastructure-adapters-uniprot-part2 — Package Family: infrastructure/adapters/uniprot (Part 2/2)](#90-pkg-infrastructure-adapters-uniprot-part2)
- [90-pkg-infrastructure-config — Package Family: infrastructure/config](#90-pkg-infrastructure-config)
- [90-pkg-infrastructure-control-plane — Package Family: infrastructure/control_plane](#90-pkg-infrastructure-control-plane)
- [90-pkg-infrastructure-export — Package Family: infrastructure/export](#90-pkg-infrastructure-export)
- [90-pkg-infrastructure-observability-anomaly — Package Family: infrastructure/observability/anomaly](#90-pkg-infrastructure-observability-anomaly)
- [90-pkg-infrastructure-schemas-part1 — Package Family: infrastructure/schemas (Part 1/3)](#90-pkg-infrastructure-schemas-part1)
- [90-pkg-infrastructure-schemas-part2 — Package Family: infrastructure/schemas (Part 2/3)](#90-pkg-infrastructure-schemas-part2)
- [90-pkg-infrastructure-schemas-part3 — Package Family: infrastructure/schemas (Part 3/3)](#90-pkg-infrastructure-schemas-part3)
- [90-pkg-infrastructure-storage-bronze — Package Family: infrastructure/storage/bronze](#90-pkg-infrastructure-storage-bronze)
- [90-pkg-infrastructure-storage-delta — Package Family: infrastructure/storage/delta](#90-pkg-infrastructure-storage-delta)
- [90-pkg-infrastructure-storage-gold-part1 — Package Family: infrastructure/storage/gold (Part 1/2)](#90-pkg-infrastructure-storage-gold-part1)
- [90-pkg-infrastructure-storage-gold-part2 — Package Family: infrastructure/storage/gold (Part 2/2)](#90-pkg-infrastructure-storage-gold-part2)
- [90-pkg-infrastructure-storage-metadata — Package Family: infrastructure/storage/metadata](#90-pkg-infrastructure-storage-metadata)
- [90-pkg-infrastructure-storage-silver-part1 — Package Family: infrastructure/storage/silver (Part 1/2)](#90-pkg-infrastructure-storage-silver-part1)
- [90-pkg-infrastructure-storage-silver-part2 — Package Family: infrastructure/storage/silver (Part 2/2)](#90-pkg-infrastructure-storage-silver-part2)
- [90-pkg-infrastructure-storage-support — Package Family: infrastructure/storage/support](#90-pkg-infrastructure-storage-support)
- [90-pkg-infrastructure-validation — Package Family: infrastructure/validation](#90-pkg-infrastructure-validation)
- [90-pkg-interfaces-cli-commands-domains-quarantine — Package Family: interfaces/cli/commands/domains/quarantine](#90-pkg-interfaces-cli-commands-domains-quarantine)
- [90-pkg-interfaces-cli-commands-domains-run-all — Package Family: interfaces/cli/commands/domains/run_all](#90-pkg-interfaces-cli-commands-domains-run-all)
- [90-pkg-interfaces-cli-commands-domains-run — Package Family: interfaces/cli/commands/domains/run](#90-pkg-interfaces-cli-commands-domains-run)
- [90-pkg-interfaces-http — Package Family: interfaces/http](#90-pkg-interfaces-http)

\\newpage

<div style="page-break-before: always;"></div>

## 01-domain-ports

**Class Diagram: Domain Port Protocols**

![01-domain-ports](../class-diagrams/svg/01-domain-ports.svg)

### Описание

Диаграмма «Class Diagram: Domain Port Protocols» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: All Protocol interfaces defined in domain/ports/. Схема имеет плотность порядка 19 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-16`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 01a-domain-ports-method-catalog

**Class Diagram: Domain Port Method Catalog (L2)**

![01a-domain-ports-method-catalog](../class-diagrams/svg/01a-domain-ports-method-catalog.svg)

### Описание

Диаграмма «Class Diagram: Domain Port Method Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed method surface extracted from 01-domain-ports L1 overview.. Схема имеет плотность порядка 13 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 02-entities-aggregates

**Class Diagram: Entities & Aggregates**

![02-entities-aggregates](../class-diagrams/svg/02-entities-aggregates.svg)

### Описание

Диаграмма «Class Diagram: Entities & Aggregates» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain entities, aggregate roots, and their relationships.. Схема имеет плотность порядка 13 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BaseEntity, Bioactivity, BioactivityState, PublicationBase, Batch, BatchRecord.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 03-value-objects

**Class Diagram: Value Objects**

![03-value-objects](../class-diagrams/svg/03-value-objects.svg)

### Описание

Диаграмма «Class Diagram: Value Objects» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Immutable domain value objects.. Схема имеет плотность порядка 17 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BronzeWriteResult, SilverWriteResult, RunContext, HealthCheckResult, FencingToken, LockContext.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `17`

\\newpage

<div style="page-break-before: always;"></div>

## 04-types-enums

**Class Diagram: Types & Enums**

![04-types-enums](../class-diagrams/svg/04-types-enums.svg)

### Описание

Диаграмма «Class Diagram: Types & Enums» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: All type aliases, NewTypes, and enumerations.. Схема имеет плотность порядка 19 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: RunID, EntityID, ContentHash, BatchID, RunType, PublicationType.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 05-exceptions

**Class Diagram: Exception Hierarchy**

![05-exceptions](../class-diagrams/svg/05-exceptions.svg)

### Описание

Диаграмма «Class Diagram: Exception Hierarchy» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain exception tree.. Схема имеет плотность порядка 19 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BioETLError, CriticalError, RecoverableError, DataQualityError, ValidationError, SchemaViolationError.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 06-config-classes

**Class Diagram: Configuration Classes**

![06-config-classes](../class-diagrams/svg/06-config-classes.svg)

### Описание

Диаграмма «Class Diagram: Configuration Classes» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Domain and application configuration hierarchy.. Схема имеет плотность порядка 14 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: RuntimeConfig, PipelineConfig, TableConfig, DQConfig, SilverFilterConfig, GoldFilterConfig.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 07-application-core-services-frontmatter-sandbox

**07 Application Core Services Frontmatter Sandbox**

![07-application-core-services-frontmatter-sandbox](../class-diagrams/svg/07-application-core-services-frontmatter-sandbox.svg)

### Описание

Диаграмма «07 Application Core Services Frontmatter Sandbox» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram). Схема имеет плотность порядка 18 узлов и 20 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Runner Core, Batch Processing, Execution Managers, Support Services. Показательные узлы для быстрого чтения: PipelineRunner, PipelineService, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManagerService.

### Метаданные

- Тип: `classdiagram`

\\newpage

<div style="page-break-before: always;"></div>

## 07-application-core-services

**Class Diagram: Application Core Services**

![07-application-core-services](../class-diagrams/svg/07-application-core-services.svg)

### Описание

Диаграмма «Class Diagram: Application Core Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: PipelineRunner, BatchExecutor, and their composition.. Схема имеет плотность порядка 18 узлов и 19 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Runner Core, Batch Processing, Execution Managers, Support Services. Показательные узлы для быстрого чтения: PipelineRunner, PipelineService, BatchExecutor, BatchTransformer, BatchWriter, BatchMemoryManagerService.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-24`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 08-application-services

**Class Diagram: Application Services**

![08-application-services](../class-diagrams/svg/08-application-services.svg)

### Описание

Диаграмма «Class Diagram: Application Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: High-level application services.. Схема имеет плотность порядка 19 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Core Application, Operational Services, DQ Analyzers. Показательные узлы для быстрого чтения: DataQualityService, DQReportService, MedallionLifecycleService, VacuumService, PipelineObserver, LifecyclePhase.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-26`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 08a-application-services-operation-catalog

**Class Diagram: Application Service Operation Catalog (L2)**

![08a-application-services-operation-catalog](../class-diagrams/svg/08a-application-services-operation-catalog.svg)

### Описание

Диаграмма «Class Diagram: Application Service Operation Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed operational methods extracted from 08-application-services L1 overview.. Схема имеет плотность порядка 9 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: MedallionLifecycleService, VacuumService, PipelineObserver, CheckpointService, MetricsService, QuarantineService.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 09-transformers

**Class Diagram: Transformers**

![09-transformers](../class-diagrams/svg/09-transformers.svg)

### Описание

Диаграмма «Class Diagram: Transformers» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: BaseTransformer hierarchy and provider-specific implementations.. Схема имеет плотность порядка 20 узлов и 19 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Base Layer, ChEMBL Transformers, Publication Enrichers, Other Providers. Показательные узлы для быстрого чтения: BaseTransformer, BaseChemblTransformer, BasePublicationTransformer, ActivityTransformer, AssayTransformer, MoleculeTransformer.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-19`
- Узлы (metadata): `20`

\\newpage

<div style="page-break-before: always;"></div>

## 10-adapters

**Class Diagram: Infrastructure Adapters**

![10-adapters](../class-diagrams/svg/10-adapters.svg)

### Описание

Диаграмма «Class Diagram: Infrastructure Adapters» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: HTTP adapter class hierarchy with mixins.. Схема имеет плотность порядка 18 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: HealthCheckMixin, HealthCheckProviderMixin, BaseHttpAdapter, BaseSyncAdapter, UnifiedHTTPClient, ChemblAdapter.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-08`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 11-storage

**Class Diagram: Storage Components**

![11-storage](../class-diagrams/svg/11-storage.svg)

### Описание

Диаграмма «Class Diagram: Storage Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Bronze/Silver/Gold writers and supporting classes.. Схема имеет плотность порядка 19 узлов и 21 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-19`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 12-composite-pipeline

**Class Diagram: Composite Pipeline Components**

![12-composite-pipeline](../class-diagrams/svg/12-composite-pipeline.svg)

### Описание

Диаграмма «Class Diagram: Composite Pipeline Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Runner, coordinators, merge service, and FSM.. Схема имеет плотность порядка 14 узлов и 13 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-01`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 13-domain-services

**Class Diagram: Domain Services**

![13-domain-services](../class-diagrams/svg/13-domain-services.svg)

### Описание

Диаграмма «Class Diagram: Domain Services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Pure domain services without I/O.. Схема имеет плотность порядка 10 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: IdentityService, NormalizationService, DataNormalizationService, AuthorNormalizationService, ActivityAggregator, UnitConverter.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 14-observability

**Class Diagram: Observability Components**

![14-observability](../class-diagrams/svg/14-observability.svg)

### Описание

Диаграмма «Class Diagram: Observability Components» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Logging, metrics, tracing implementations.. Схема имеет плотность порядка 19 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: LoggerPort, UnifiedLogger, StructlogLogger, NoOpLogger, MetricsPort, MetricsCollector.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 14a-observability-method-catalog

**Class Diagram: Observability Method Catalog (L2)**

![14a-observability-method-catalog](../class-diagrams/svg/14a-observability-method-catalog.svg)

### Описание

Диаграмма «Class Diagram: Observability Method Catalog (L2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Detailed method surface extracted from 14-observability L1 overview.. Схема имеет плотность порядка 9 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: LoggerPort, UnifiedLogger, MetricsPort, MetricsCollector, PrometheusMetrics, MetricsServerAdapter.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-02`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 15-extractors

**Class Diagram: Field Extractors and Publication Blocks**

![15-extractors](../class-diagrams/svg/15-extractors.svg)

### Описание

Диаграмма «Class Diagram: Field Extractors and Publication Blocks» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Helper extractor classes plus declarative block contract used in publication transformers.. Схема имеет плотность порядка 14 узлов и 17 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: PubMedExtractors, UniProtExtractors. Показательные узлы для быстрого чтения: BaseFieldExtractor, ExtractionBlock, AbstractExtractor, AuthorExtractor, DateExtractor, ClassificationExtractor.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-19`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 16-factories-bootstrap

**Class Diagram: Factories & Bootstrap**

![16-factories-bootstrap](../class-diagrams/svg/16-factories-bootstrap.svg)

### Описание

Диаграмма «Class Diagram: Factories & Bootstrap» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Class / Interface». В комментариях исходника зафиксирован фокус диаграммы: Current composition-layer factories, provider registry, and runtime assembly.. Схема имеет плотность порядка 9 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: ProviderRegistry, ProviderDataSourceCatalog, DataSourceFactory, PipelineRegistry, RunnerFactory, RunnerFactoryBuilderService.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата: `2026-03-16`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-composite-checkpoint

**Package Family: application/composite/checkpoint**

![90-pkg-application-composite-checkpoint](../class-diagrams/svg/90-pkg-application-composite-checkpoint.svg)

### Описание

Диаграмма «Package Family: application/composite/checkpoint» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/composite/checkpoint; modules: anchor_context, \_anchor_context, load_service, persistence_service, service, state.. Схема имеет плотность порядка 5 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: anchor context, load service, persistence service, service, state. Показательные узлы для быстрого чтения: ExpectedCheckpointContext, CompositeCheckpointLoadService, CompositeCheckpointPersistenceService, CompositeCheckpointService, CompositeCheckpointState. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-composite-runner-pkg-part1

**Package Family: application/composite/runner_pkg (Part 1/2)**

![90-pkg-application-composite-runner-pkg-part1](../class-diagrams/svg/90-pkg-application-composite-runner-pkg-part1.svg)

### Описание

Диаграмма «Package Family: application/composite/runner_pkg (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/application/composite/runner_pkg; part 1/2; modules: runner_completion_helpers, runner_runtime_helpers, runner_execution_orchestrator, runner_merge_stage_types, runner_models, runner_stage_types.. Схема имеет плотность порядка 30 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: runner completion helpers, runner runtime helpers, runner execution orchestrator, runner merge stage types, runner models, runner stage types. Показательные узлы для быстрого чтения: CompositePipelineFinalizationContext, CompositePipelineFinalizationResult, CompositeResultBuildContext, \_CompositePipelineFinalizationHostProtocol, ManagedCompositeLockContext, \_CheckpointManagerProtocol. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `30`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-composite-runner-pkg-part2

**Package Family: application/composite/runner_pkg (Part 2/2)**

![90-pkg-application-composite-runner-pkg-part2](../class-diagrams/svg/90-pkg-application-composite-runner-pkg-part2.svg)

### Описание

Диаграмма «Package Family: application/composite/runner_pkg (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/application/composite/runner_pkg; part 2/2; modules: runner_merge_stage_mixin, runner_stage_enrichment_mixin, runner_stage_mixin, runner_stage_support_mixin, runner_stage_support_types, runner_support_mixin.. Схема имеет плотность порядка 6 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: runner merge stage mixin, runner stage enrichment mixin, runner stage mixin, runner stage support mixin, runner stage support types, runner support mixin. Показательные узлы для быстрого чтения: CompositeRunnerMergeStageMixin, \_CompositeRunnerStageEnrichmentMixin, CompositeRunnerStageMixin, \_CompositeRunnerStageSupportMixin, \_CompositeRunnerStageSupportHostProtocol, CompositeRunnerSupportMixin. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-core-base-transformer

**Package Family: application/core/base_transformer**

![90-pkg-application-core-base-transformer](../class-diagrams/svg/90-pkg-application-core-base-transformer.svg)

### Описание

Диаграмма «Package Family: application/core/base_transformer» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/core/base_transformer; modules: errors, types, base, contract_policy.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: errors, types, base, contract policy. Показательные узлы для быстрого чтения: FilteredOutError, TransformationError, TransformerDependencyContext, ValueObjectWithFromRaw, BaseTransformer, \_DefaultContractPolicy. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-core-batch-execution

**Package Family: application/core/batch_execution**

![90-pkg-application-core-batch-execution](../class-diagrams/svg/90-pkg-application-core-batch-execution.svg)

### Описание

Диаграмма «Package Family: application/core/batch_execution» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/core/batch_execution; modules: lifecycle, \_contracts, run_service, state_service.. Схема имеет плотность порядка 15 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: lifecycle, contracts, run service, state service. Показательные узлы для быстрого чтения: BatchExecutionContext, BatchExecutionFinalizationContext, BatchExecutionLifecycleContext, BatchExecutionLifecycleService, \_BatchCheckpointRecoveryLifecyclePort, \_BatchProgressInitializerPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-core-lifecycle

**Package Family: application/core/lifecycle**

![90-pkg-application-core-lifecycle](../class-diagrams/svg/90-pkg-application-core-lifecycle.svg)

### Описание

Диаграмма «Package Family: application/core/lifecycle» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/core/lifecycle; modules: batch_fsm, cleanup_service, checkpoint_manager, heartbeat, lock_runtime_service, lock_manager, shutdown.. Схема имеет плотность порядка 15 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: batch fsm, cleanup service, checkpoint manager, heartbeat, lock runtime service, legacy lock shim, shutdown. Показательные узлы для быстрого чтения: BatchExecutionCommandTask, BatchExecutionCoordinator, BatchExecutionEventSignal, BatchExecutionState, BatchExecutionTransitionResult, IllegalStateTransitionError. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-core-postrun

**Package Family: application/core/postrun**

![90-pkg-application-core-postrun](../class-diagrams/svg/90-pkg-application-core-postrun.svg)

### Описание

Диаграмма «Package Family: application/core/postrun» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/core/postrun; modules: \_failure_policy, service, compact_orchestrator, \_service_collaborators, cleanup_orchestrator, dq_report_orchestrator.. Схема имеет плотность порядка 15 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: failure policy, service, compact orchestrator, service collaborators, cleanup orchestrator, dq report orchestrator. Показательные узлы для быстрого чтения: PostrunFailureHandlingMixin, PostrunFailurePolicySpec, PostrunStrictValidationMixin, \_HasPostrunFailureHandling, \_HasPostrunRuntime, PostrunDependencyContext. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-core-preflight

**Package Family: application/core/preflight**

![90-pkg-application-core-preflight](../class-diagrams/svg/90-pkg-application-core-preflight.svg)

### Описание

Диаграмма «Package Family: application/core/preflight» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/core/preflight; modules: health_aggregator, medallion_validator, preflight_reporting, service.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: health aggregator, medallion validator, preflight reporting, service. Показательные узлы для быстрого чтения: HealthAggregator, MedallionConfigValidator, \_PreflightLoggingHostProtocol, PreflightService. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-observability

**Package Family: application/observability**

![90-pkg-application-observability](../class-diagrams/svg/90-pkg-application-observability.svg)

### Описание

Диаграмма «Package Family: application/observability» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/observability; modules: observer, observer_context_mixin, observer_event_mixin.. Схема имеет плотность порядка 5 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: observer, observer context mixin, observer event mixin. Показательные узлы для быстрого чтения: LifecyclePhase, PipelineObserver, \_ObserverLifecycleEmissionMixin, \_ObserverContextManagerMixin, \_ObserverEventMixin. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-pipelines-chembl

**Package Family: application/pipelines/chembl**

![90-pkg-application-pipelines-chembl](../class-diagrams/svg/90-pkg-application-pipelines-chembl.svg)

### Описание

Диаграмма «Package Family: application/pipelines/chembl» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/pipelines/chembl; modules: pipeline_types, activity_transformer, assay_parameters_transformer, assay_transformer, base_chembl_transformer, cell_line_transformer.. Схема имеет плотность порядка 29 узлов и 14 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: pipeline types, activity transformer, assay parameters transformer, assay transformer, base chembl transformer, cell line transformer. Показательные узлы для быстрого чтения: ChEMBLActivityPipeline, ChEMBLAssayParametersPipeline, ChEMBLAssayPipeline, ChEMBLCellLinePipeline, ChEMBLCompoundRecordPipeline, ChEMBLMoleculePipeline. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-pipelines-common

**Package Family: application/pipelines/common**

![90-pkg-application-pipelines-common](../class-diagrams/svg/90-pkg-application-pipelines-common.svg)

### Описание

Диаграмма «Package Family: application/pipelines/common» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/pipelines/common; modules: blocks, base_publication_transformer, publication_blocks.. Схема имеет плотность порядка 7 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: blocks, base publication transformer, publication blocks. Показательные узлы для быстрого чтения: \_CrossRefAuthorBlock, \_CrossRefCoreBlock, \_CrossRefDateBlock, \_CrossRefJournalBlock, \_CrossRefMetadataBlock, BasePublicationTransformer. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-pipelines-pubmed

**Package Family: application/pipelines/pubmed**

![90-pkg-application-pipelines-pubmed](../class-diagrams/svg/90-pkg-application-pipelines-pubmed.svg)

### Описание

Диаграмма «Package Family: application/pipelines/pubmed» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/pipelines/pubmed; modules: block_definitions, __init__, transformer.. Схема имеет плотность порядка 10 узлов и 7 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: block definitions, init, transformer. Показательные узлы для быстрого чтения: \_PubMedAuthorBlock, \_PubMedClassificationBlock, \_PubMedCoreBlock, \_PubMedDateBlock, \_PubMedIdentifierBlock, \_PubMedJournalBlock. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-pipelines-uniprot-extractors

**Package Family: application/pipelines/uniprot/extractors**

![90-pkg-application-pipelines-uniprot-extractors](../class-diagrams/svg/90-pkg-application-pipelines-uniprot-extractors.svg)

### Описание

Диаграмма «Package Family: application/pipelines/uniprot/extractors» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/pipelines/uniprot/extractors; modules: \_feature_wrappers_mixin, comments, crossrefs, extractor_helpers, features, genes.. Схема имеет плотность порядка 8 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: feature wrappers mixin, comments, crossrefs, extractor helpers, features, genes. Показательные узлы для быстрого чтения: FeatureExtractionWrappersMixin, \_FeatureExtractorProtocol, CommentExtractor, CrossRefExtractor, ExtractorHelper, FeatureExtractor. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `8`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-pipelines-uniprot

**Package Family: application/pipelines/uniprot**

![90-pkg-application-pipelines-uniprot](../class-diagrams/svg/90-pkg-application-pipelines-uniprot.svg)

### Описание

Диаграмма «Package Family: application/pipelines/uniprot» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/pipelines/uniprot; modules: __init__, idmapping_transformer, transformer, transformer_business_data_mixin.. Схема имеет плотность порядка 4 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: init, idmapping transformer, transformer, transformer business data mixin. Показательные узлы для быстрого чтения: UniProtProteinPipeline, IDMappingTransformer, UniProtProteinTransformer, UniProtBusinessDataMixin. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-application-services-dq

**Package Family: application/services/dq**

![90-pkg-application-services-dq](../class-diagrams/svg/90-pkg-application-services-dq.svg)

### Описание

Диаграмма «Package Family: application/services/dq» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/application/services/dq; modules: bronze_analyzer, gold_analyzer, silver_analyzer, silver_check_executor, silver_statistics, silver_threshold.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: bronze analyzer, gold analyzer, silver analyzer, silver check executor, silver statistics, silver threshold. Показательные узлы для быстрого чтения: BronzeDQAnalyzer, GoldDQAnalyzer, SilverDQAnalyzer, SilverCheckExecutor, SilverStatisticsCalculator, SilverThresholdChecker. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-bootstrap-runtime

**Package Family: composition/bootstrap/runtime**

![90-pkg-composition-bootstrap-runtime](../class-diagrams/svg/90-pkg-composition-bootstrap-runtime.svg)

### Описание

Диаграмма «Package Family: composition/bootstrap/runtime» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/bootstrap/runtime; modules: composite_support_service_bundles, composite_support_services_factory, runner_factory_builder_service, composite, composite_filter_extraction_service, composite_infrastructure_context.. Схема имеет плотность порядка 10 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: composite support service bundles, composite support services factory, runner factory builder service, composite, composite filter extraction service, composite infrastructure context. Показательные узлы для быстрого чтения: ExecutionSupportServicesBundle, MergeDependenciesBundle, RuntimeManagementServicesBundle, CompositeSupportServices, CompositeSupportServicesFactory, BronzeRunOptions. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-factories-datasource

**Package Family: composition/factories/datasource**

![90-pkg-composition-factories-datasource](../class-diagrams/svg/90-pkg-composition-factories-datasource.svg)

### Описание

Диаграмма «Package Family: composition/factories/datasource» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/factories/datasource; modules: adapter_helpers, data_source_factory, http_client, pubchem.. Схема имеет плотность порядка 7 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: adapter helpers, data source factory, http client, pubchem. Показательные узлы для быстрого чтения: AdapterHelperServices, AdapterHelpersFactory, SyncAdapterHelperServices, DataSourceFactory, HttpClientFactory, ResolvedHttpConfig. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-factories-services

**Package Family: composition/factories/services**

![90-pkg-composition-factories-services](../class-diagrams/svg/90-pkg-composition-factories-services.svg)

### Описание

Диаграмма «Package Family: composition/factories/services» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/factories/services; modules: builder, bundle, common_service_wiring, factory, polars_join_adapter.. Схема имеет плотность порядка 5 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: builder, bundle, common service wiring, factory, polars join adapter. Показательные узлы для быстрого чтения: ServicesBuilder, ServiceBundleDependencies, CommonServicePorts, BaseServicesFactory, PolarsJoinAdapter. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-factories-storage

**Package Family: composition/factories/storage**

![90-pkg-composition-factories-storage](../class-diagrams/svg/90-pkg-composition-factories-storage.svg)

### Описание

Диаграмма «Package Family: composition/factories/storage» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/factories/storage; modules: factory, merged_mixin, \_helpers, adapter, clear_mixin, health_mixin.. Схема имеет плотность порядка 10 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: factory, merged mixin, helpers, adapter, clear mixin, health mixin. Показательные узлы для быстрого чтения: StorageContext, StorageFactory, StorageAdapterMergedMixin, \_SilverMergedWriteProtocol, StorageCreationContext, StorageAdapter. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-providers

**Package Family: composition/providers**

![90-pkg-composition-providers](../class-diagrams/svg/90-pkg-composition-providers.svg)

### Описание

Диаграмма «Package Family: composition/providers» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/providers; modules: \_default_registry, \_models, \_registration_contracts, \_registration_biblio_profiles, \_creation, \_registry_protocols.. Схема имеет плотность порядка 21 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: default registry, models, registration contracts, registration biblio profiles, creation, registry protocols. Показательные узлы для быстрого чтения: DefaultRegistryMethod, ProvidersDescriptor, \_SupportsDefaultRegistry, \_SupportsProviderRegistryStore, \_SupportsProviderStore, DataSourceCreatorProtocol. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `21`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition-runtime-builders

**Package Family: composition/runtime_builders**

![90-pkg-composition-runtime-builders](../class-diagrams/svg/90-pkg-composition-runtime-builders.svg)

### Описание

Диаграмма «Package Family: composition/runtime_builders» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition/runtime_builders; modules: inputs_resolver, inputs_runtime_helpers, run_manifest_builder, runner_builder.. Схема имеет плотность порядка 7 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: inputs resolver, inputs runtime helpers, run manifest builder, runner builder. Показательные узлы для быстрого чтения: ResolvedVacuumSettings, RunnerInputs, \_PaginationConfigLike, \_SourceConfigLike, ResolvedRuntimeProjection, \_ManifestControlPlaneRefs. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-composition

**Package Family: composition**

![90-pkg-composition](../class-diagrams/svg/90-pkg-composition.svg)

### Описание

Диаграмма «Package Family: composition» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/composition; modules: bootstrap_contexts, \_pipeline_execution, observability, registry, bootstrap_logger, builders.. Схема имеет плотность порядка 12 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: bootstrap contexts, pipeline execution, observability, registry, bootstrap logger, builders. Показательные узлы для быстрого чтения: DQConfigsContext, DQOutputPathsContext, PipelineCallbacksContext, RateLimitContext, ArchiveOptions, VacuumOptions. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-aggregates

**Package Family: domain/aggregates**

![90-pkg-domain-aggregates](../class-diagrams/svg/90-pkg-domain-aggregates.svg)

### Описание

Диаграмма «Package Family: domain/aggregates» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/aggregates; modules: events, \_batch_mixins, \_pipeline_run_read_model_mixin, \_quarantine_value_objects, pipeline_run_state, \_batch_aggregate.. Схема имеет плотность порядка 30 узлов и 21 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: events, batch mixins, pipeline run read model mixin, quarantine value objects, pipeline run state, batch aggregate. Показательные узлы для быстрого чтения: BatchCreated, BatchFailed, BatchSealed, BatchWritten, DomainEvent, PipelineCompleted. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `30`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-composite-part1

**Package Family: domain/composite (Part 1/2)**

![90-pkg-domain-composite-part1](../class-diagrams/svg/90-pkg-domain-composite-part1.svg)

### Описание

Диаграмма «Package Family: domain/composite (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/domain/composite; part 1/2; modules: cross_validation, aggregation, config_models, lineage, result_seed_dependency, strategy.. Схема имеет плотность порядка 29 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: cross validation, aggregation, config models, lineage, result seed dependency, strategy. Показательные узлы для быстрого чтения: ComparisonMethod, CrossValidationStats, CrossValidationVerdict, EnricherCVStats, EnricherFieldPairing, FieldComparisonSpec. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-composite-part2

**Package Family: domain/composite (Part 2/2)**

![90-pkg-domain-composite-part2](../class-diagrams/svg/90-pkg-domain-composite-part2.svg)

### Описание

Диаграмма «Package Family: domain/composite (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/domain/composite; part 2/2; modules: config_runtime, config_schema, field_groups_models, result_enrichment, config, field_groups_registry.. Схема имеет плотность порядка 13 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: config runtime, config schema, field groups models, result enrichment, config, field groups registry. Показательные узлы для быстрого чтения: ExecutionConfig, LineageConfig, DataSchemaConfig, LayerColumnConfig, FieldGroupDefinition, FieldMapping. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-contracts-gold

**Package Family: domain/contracts/gold**

![90-pkg-domain-contracts-gold](../class-diagrams/svg/90-pkg-domain-contracts-gold.svg)

### Описание

Диаграмма «Package Family: domain/contracts/gold» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/contracts/gold; modules: \_chembl_reference_publication_schemas, \_chembl_target_lookup_schemas, \_chembl_activity_assay_schemas, composite_bioassay, \_chembl_molecule_protein_schemas, uniprot.. Схема имеет плотность порядка 26 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: chembl reference publication schemas, chembl target lookup schemas, chembl activity assay schemas, composite bioassay, chembl molecule protein schemas, uniprot. Показательные узлы для быстрого чтения: ChEMBLCellLineGoldSchema, ChEMBLCompoundRecordGoldSchema, ChEMBLPublicationGoldSchema, ChEMBLPublicationSimilarityGoldSchema, ChEMBLPublicationTermGoldSchema, ChEMBLSubcellularFractionGoldSchema. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `26`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-control-plane

**Package Family: domain/control_plane**

![90-pkg-domain-control-plane](../class-diagrams/svg/90-pkg-domain-control-plane.svg)

### Описание

Диаграмма «Package Family: domain/control_plane» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/control_plane; modules: effective_config_artifact, contract_registry_types, gold_contract, run_manifest, contract_registry_service, run_ledger.. Схема имеет плотность порядка 25 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: effective config artifact, contract registry types, gold contract, run manifest, contract registry service, run ledger. Показательные узлы для быстрого чтения: ConfigResolutionPolicy, ConfigSourceRef, DQPolicySnapshot, EffectiveConfigArtifact, EffectiveConfigHashes, EffectiveExecutionConfig. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-04-02`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-exceptions-infrastructure

**Package Family: domain/exceptions/infrastructure**

![90-pkg-domain-exceptions-infrastructure](../class-diagrams/svg/90-pkg-domain-exceptions-infrastructure.svg)

### Описание

Диаграмма «Package Family: domain/exceptions/infrastructure» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/exceptions/infrastructure; modules: \_storage, \_base.. Схема имеет плотность порядка 5 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: storage, base. Показательные узлы для быстрого чтения: SchemaEvolutionError, StorageError, StorageQuotaExceededError, TableNotFoundError, InfrastructureError. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-exceptions-network

**Package Family: domain/exceptions/network**

![90-pkg-domain-exceptions-network](../class-diagrams/svg/90-pkg-domain-exceptions-network.svg)

### Описание

Диаграмма «Package Family: domain/exceptions/network» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/exceptions/network; modules: service, connection, timeout.. Схема имеет плотность порядка 9 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: service, connection, timeout. Показательные узлы для быстрого чтения: ApiError, ExternalServiceError, RateLimitError, ServiceAuthenticationError, ServiceUnavailableError, NetworkError. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-filtering

**Package Family: domain/filtering**

![90-pkg-domain-filtering](../class-diagrams/svg/90-pkg-domain-filtering.svg)

### Описание

Диаграмма «Package Family: domain/filtering» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/filtering; modules: column_filter, input_config, list_filters, \_base_filter_config, gold_config, load_result.. Схема имеет плотность порядка 11 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: column filter, input config, list filters, base filter config, gold config, load result. Показательные узлы для быстрого чтения: FilterOperator, GoldColumnFilter, FilterColumn, InputFilterConfig, GoldListContainsFilter, GoldListLengthFilter. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-lineage

**Package Family: domain/lineage**

![90-pkg-domain-lineage](../class-diagrams/svg/90-pkg-domain-lineage.svg)

### Описание

Диаграмма «Package Family: domain/lineage» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/lineage; modules: refs, graph.. Схема имеет плотность порядка 8 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: refs, graph. Показательные узлы для быстрого чтения: DatasetRef, LineageNodeRef, LineageNodeType, SchemaRef, TransformRef, LineageEdge. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `8`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-models

**Package Family: domain/models**

![90-pkg-domain-models](../class-diagrams/svg/90-pkg-domain-models.svg)

### Описание

Диаграмма «Package Family: domain/models» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/models; modules: \_metadata_common, \_metadata_gold, \_metadata_silver, \_metadata_bronze, filter.. Схема имеет плотность порядка 29 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: metadata common, metadata gold, metadata silver, metadata bronze, filter. Показательные узлы для быстрого чтения: BaseOutputMetadata, EnvironmentMetadata, GovernanceLineageConfig, GovernanceMetadata, PipelineMetadata, QualityExpectations. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-config

**Package Family: domain/ports/config**

![90-pkg-domain-ports-config](../class-diagrams/svg/90-pkg-domain-ports-config.svg)

### Описание

Диаграмма «Package Family: domain/ports/config» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/config; modules: config_loader_port, config_port.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: config loader port, config port. Показательные узлы для быстрого чтения: DomainConfigMapperPort, PipelineConfigLoaderPort, SettingsLoaderPort, PipelineSettingsPort, PipelineYamlConfigPort, SettingsPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-metadata

**Package Family: domain/ports/metadata**

![90-pkg-domain-ports-metadata](../class-diagrams/svg/90-pkg-domain-ports-metadata.svg)

### Описание

Диаграмма «Package Family: domain/ports/metadata» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/metadata; modules: coordinator, writer.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: coordinator, writer. Показательные узлы для быстрого чтения: BronzeMetadataInput, GoldMetadataInput, MetadataCoordinatorPort, SilverMetadataInput, SilverRef, MetadataWriterPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-noop

**Package Family: domain/ports/noop**

![90-pkg-domain-ports-noop](../class-diagrams/svg/90-pkg-domain-ports-noop.svg)

### Описание

Диаграмма «Package Family: domain/ports/noop» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/noop; modules: \_tracing, \_audit_pii, \_memory_metadata, \_debug, \_metrics.. Схема имеет плотность порядка 9 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: tracing, audit pii, memory metadata, debug, metrics. Показательные узлы для быстрого чтения: NoOpTracing, \_NoOpOtelTracer, \_NoOpSpan, NoOpAudit, NoOpPiiHasher, NoOpMemoryMonitor. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-observability

**Package Family: domain/ports/observability**

![90-pkg-domain-ports-observability](../class-diagrams/svg/90-pkg-domain-ports-observability.svg)

### Описание

Диаграмма «Package Family: domain/ports/observability» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/observability; modules: metrics, dq_monitor, logging, tracing.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: metrics, dq monitor, logging, tracing. Показательные узлы для быстрого чтения: ExecutorMetricsPort, MetricsPort, MetricsServerPort, DQMonitorPort, LoggerPort, TracingPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-quality

**Package Family: domain/ports/quality**

![90-pkg-domain-ports-quality](../class-diagrams/svg/90-pkg-domain-ports-quality.svg)

### Описание

Диаграмма «Package Family: domain/ports/quality» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/quality; modules: dq_report, dq_config, quarantine, validation, contract_policy, error_classifier.. Схема имеет плотность порядка 15 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: dq report, dq config, quarantine, validation, contract policy, error classifier. Показательные узлы для быстрого чтения: BronzeDQAnalyzerPort, DQReportWriterPort, GoldDQAnalyzerPort, SilverDQAnalyzerPort, BronzeDQConfigPort, GoldDQConfigPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-runtime

**Package Family: domain/ports/runtime**

![90-pkg-domain-ports-runtime](../class-diagrams/svg/90-pkg-domain-ports-runtime.svg)

### Описание

Диаграмма «Package Family: domain/ports/runtime» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/runtime; modules: runner, pipeline_debug, memory, registry_port, batch_id, checkpoint.. Схема имеет плотность порядка 22 узлов и 2 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: runner, pipeline debug, memory, registry port, batch id, checkpoint. Показательные узлы для быстрого чтения: ExecutionMetricsReadablePort, ExecutionMetricsRunnerPort, ExecutionObservabilityPort, MetricsExtractorPort, PipelineFactoryPort, RunnablePort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `22`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-ports-storage

**Package Family: domain/ports/storage**

![90-pkg-domain-ports-storage](../class-diagrams/svg/90-pkg-domain-ports-storage.svg)

### Описание

Диаграмма «Package Family: domain/ports/storage» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/ports/storage; modules: aggregate_port, bronze_port, gold_port, lifecycle_port, merged_port, silver_port.. Схема имеет плотность порядка 6 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: aggregate port, bronze port, gold port, lifecycle port, merged port, silver port. Показательные узлы для быстрого чтения: StoragePort, BronzeStoragePort, GoldStoragePort, StorageLifecyclePort, MergedStoragePort, SilverStoragePort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-schemas-chembl

**Package Family: domain/schemas/chembl**

![90-pkg-domain-schemas-chembl](../class-diagrams/svg/90-pkg-domain-schemas-chembl.svg)

### Описание

Диаграмма «Package Family: domain/schemas/chembl» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/schemas/chembl; modules: activity, assay, assay_parameters, cell_line, compound_record, molecule.. Схема имеет плотность порядка 12 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: activity, assay, assay parameters, cell line, compound record, molecule. Показательные узлы для быстрого чтения: ActivitySchema, AssaySchema, AssayParametersSchema, CellLineSchema, CompoundRecordSchema, MoleculeSchema. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-schemas-pubchem

**Package Family: domain/schemas/pubchem**

![90-pkg-domain-schemas-pubchem](../class-diagrams/svg/90-pkg-domain-schemas-pubchem.svg)

### Описание

Диаграмма «Package Family: domain/schemas/pubchem» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/schemas/pubchem; modules: \_identifiers, \_physchem, \_stereo, \_three_d, compound.. Схема имеет плотность порядка 5 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: identifiers, physchem, stereo, three d, compound. Показательные узлы для быстрого чтения: PubchemIdentitySchema, PubchemPhysChemSchema, PubchemStereoSchema, PubchemThreeDSchema, PubchemMoleculeSchema. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain-schemas-uniprot

**Package Family: domain/schemas/uniprot**

![90-pkg-domain-schemas-uniprot](../class-diagrams/svg/90-pkg-domain-schemas-uniprot.svg)

### Описание

Диаграмма «Package Family: domain/schemas/uniprot» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain/schemas/uniprot; modules: \_annotations, \_core, \_features, \_xrefs, idmapping, protein.. Схема имеет плотность порядка 6 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: annotations, core, features, xrefs, idmapping, protein. Показательные узлы для быстрого чтения: UniprotAnnotationSchema, UniprotCoreSchema, UniprotFeatureSchema, UniprotXrefSchema, IDMappingSchema, UniprotTargetSchema. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-domain

**Package Family: domain**

![90-pkg-domain](../class-diagrams/svg/90-pkg-domain.svg)

### Описание

Диаграмма «Package Family: domain» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/domain; modules: medallion, locking, resilience, context, context_filtering, context_cached_bronze.. Схема имеет плотность порядка 24 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: medallion, locking, resilience, context, context filtering, context cached bronze. Показательные узлы для быстрого чтения: ClearPolicy, GoldWriteMode, Layer, LoadingStrategy, MedallionPolicy, SilverWriteMode. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `24`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-chembl-part1

**Package Family: infrastructure/adapters/chembl (Part 1/2)**

![90-pkg-infrastructure-adapters-chembl-part1](../class-diagrams/svg/90-pkg-infrastructure-adapters-chembl-part1.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/chembl (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/adapters/chembl; part 1/2; modules: models_common, models_compound, models_activity, \_fetch_paging_filtered, \_fetch_resilience_fallback, \_fetch_resilience_recovery.. Схема имеет плотность порядка 30 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: models common, models compound, models activity, fetch paging filtered, fetch resilience fallback, fetch resilience recovery. Показательные узлы для быстрого чтения: ChemblAssayRecord, ChemblAssayResponse, ChemblCellLineRecord, ChemblCellLineResponse, ChemblPageMeta, ChemblPublicationApiRecord. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `30`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-chembl-part2

**Package Family: infrastructure/adapters/chembl (Part 2/2)**

![90-pkg-infrastructure-adapters-chembl-part2](../class-diagrams/svg/90-pkg-infrastructure-adapters-chembl-part2.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/chembl (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/adapters/chembl; part 2/2; modules: health, metadata.. Схема имеет плотность порядка 2 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: health, metadata. Показательные узлы для быстрого чтения: ChemblHealthMixin, ChemblMetadataMixin. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `2`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-common

**Package Family: infrastructure/adapters/common**

![90-pkg-infrastructure-adapters-common](../class-diagrams/svg/90-pkg-infrastructure-adapters-common.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/common» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/common; modules: fallback_fetch_service, composable_fallback, dependency_context, api_request_collector, base_title_fallback, fallback_policy_mixin.. Схема имеет плотность порядка 17 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: fallback fetch service, composable fallback, dependency context, api request collector, base title fallback, fallback policy mixin. Показательные узлы для быстрого чтения: DefaultFallbackExecution, ExtractRecordIdPort, FallbackExecutionPort, FallbackFetchOrchestratorService, FallbackFetchRequest, NormalizeIdPort. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `17`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-crossref

**Package Family: infrastructure/adapters/crossref**

![90-pkg-infrastructure-adapters-crossref](../class-diagrams/svg/90-pkg-infrastructure-adapters-crossref.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/crossref» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/crossref; modules: models_shared, \_batch_support, \_response_models, response_mapper, \_client_fallback_policy, \_doi_batch_processor.. Схема имеет плотность порядка 26 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: models shared, batch support, response models, response mapper, client fallback policy, doi batch processor. Показательные узлы для быстрого чтения: CrossRefAssertion, CrossRefAuthor, CrossRefClinicalTrial, CrossRefDateParts, CrossRefFunder, CrossRefLicense. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `26`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-http

**Package Family: infrastructure/adapters/http**

![90-pkg-infrastructure-adapters-http](../class-diagrams/svg/90-pkg-infrastructure-adapters-http.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/http» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/http; modules: client_retry_observability, health_monitor, \_client_retry_models, \_health_monitor_support, circuit_breaker, client.. Схема имеет плотность порядка 17 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: client retry observability, health monitor, client retry models, health monitor support, circuit breaker, client. Показательные узлы для быстрого чтения: RetryStateLike, SpanLike, \_OtelTracerLike, HealthAdjustedConfig, ProviderHealthMonitor, ProviderHealthState. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `17`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-openalex

**Package Family: infrastructure/adapters/openalex**

![90-pkg-infrastructure-adapters-openalex](../class-diagrams/svg/90-pkg-infrastructure-adapters-openalex.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/openalex» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/openalex; modules: \_filter_fetch_requests, health_adapter_mixin, \_filter_fetch_flow, client, client_helpers_adapter_mixin, client_runtime_helpers.. Схема имеет плотность порядка 16 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: filter fetch requests, health adapter mixin, filter fetch flow, client, client helpers adapter mixin, client runtime helpers. Показательные узлы для быстрого чтения: \_FallbackFetchRequest, \_FetchRequest, \_FilteredFetchRequest, \_OpenAlexRequestHost, OpenAlexAdapterHealthMixin, \_OpenAlexHealthHost. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-pubchem

**Package Family: infrastructure/adapters/pubchem**

![90-pkg-infrastructure-adapters-pubchem](../class-diagrams/svg/90-pkg-infrastructure-adapters-pubchem.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/pubchem» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/pubchem; modules: models, fetch_flow, \_client_fetch_surface, \_fetch_strategy_search, client, client_model_mixin.. Схема имеет плотность порядка 14 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: models, fetch flow, client fetch surface, fetch strategy search, client, client model mixin. Показательные узлы для быстрого чтения: PubChemAssayRecord, PubChemBioactivityRecord, PubChemSubstanceRecord, PubchemMoleculeApiRecord, PubchemMoleculeDetailRecord, PubChemFetchFlowService. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-pubmed

**Package Family: infrastructure/adapters/pubmed**

![90-pkg-infrastructure-adapters-pubmed](../class-diagrams/svg/90-pkg-infrastructure-adapters-pubmed.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/pubmed» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/pubmed; modules: models, \_search_models, \_client_fallback_policy, \_fetch, \_filter_fetch_support, \_health.. Схема имеет плотность порядка 21 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: models, search models, client fallback policy, fetch, filter fetch support, health. Показательные узлы для быстрого чтения: PubMedArticleId, PubMedArticleRecord, PubMedAuthor, PubMedChemical, PubMedExtendedRecord, PubMedGrant. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `21`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-semanticscholar

**Package Family: infrastructure/adapters/semanticscholar**

![90-pkg-infrastructure-adapters-semanticscholar](../class-diagrams/svg/90-pkg-infrastructure-adapters-semanticscholar.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/semanticscholar» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/adapters/semanticscholar; modules: health_metadata_mixin, \_client_fallback_policy, \_search_fetch_flow, adapter, batch_request_mixin, fallback.. Схема имеет плотность порядка 14 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: health metadata mixin, client fallback policy, search fetch flow, adapter, batch request mixin, fallback. Показательные узлы для быстрого чтения: SemanticScholarAdapterMetricsProtocol, SemanticScholarHTTPClientProtocol, SemanticScholarHTTPResponseProtocol, SemanticScholarHealthMetadataDependencies, SemanticScholarHealthMetadataMixin, SemanticScholarHealthMetadataMixinABC. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-uniprot-part1

**Package Family: infrastructure/adapters/uniprot (Part 1/2)**

![90-pkg-infrastructure-adapters-uniprot-part1](../class-diagrams/svg/90-pkg-infrastructure-adapters-uniprot-part1.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/uniprot (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/adapters/uniprot; part 1/2; modules: \_uniprot_model_annotations, \_uniprot_model_structures, \_uniprot_model_records, \_idmapping_errors, \_idmapping_health, \_idmapping_retry.. Схема имеет плотность порядка 30 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: uniprot model annotations, uniprot model structures, uniprot model records, idmapping errors, idmapping health, idmapping retry. Показательные узлы для быстрого чтения: UniProtComment, UniProtEcNumber, UniProtEvidence, UniProtFullName, UniProtGene, UniProtIsoform. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `30`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-adapters-uniprot-part2

**Package Family: infrastructure/adapters/uniprot (Part 2/2)**

![90-pkg-infrastructure-adapters-uniprot-part2](../class-diagrams/svg/90-pkg-infrastructure-adapters-uniprot-part2.svg)

### Описание

Диаграмма «Package Family: infrastructure/adapters/uniprot (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/adapters/uniprot; part 2/2; modules: \_idmapping_transport, \_idmapping_parser, client, fallback_policy, fasta_parser, feature_sequence_adapter_mixin.. Схема имеет плотность порядка 11 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: idmapping transport, idmapping parser, client, fallback policy, fasta parser, feature sequence adapter mixin. Показательные узлы для быстрого чтения: IDMappingTransportDependencies, IDMappingTransportMixin, IDMappingParserMixin, UniProtAdapter, UniProtFallbackPolicy, FastaParser. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-config

**Package Family: infrastructure/config**

![90-pkg-infrastructure-config](../class-diagrams/svg/90-pkg-infrastructure-config.svg)

### Описание

Диаграмма «Package Family: infrastructure/config» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/config; modules: domain_config_resolver, \_base, contract_policy_validation, \_yaml_settings_source, base_config_loader, composite_config_api.. Схема имеет плотность порядка 21 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: domain config resolver, base, contract policy validation, yaml settings source, base config loader, composite config api. Показательные узлы для быстрого чтения: DomainConfigMapper, DomainConfigResolver, PipelineConfigDQResolver, PipelineConfigDQResolverBuilder, ObservabilitySettings, PipelineSettings. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `21`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-control-plane

**Package Family: infrastructure/control_plane**

![90-pkg-infrastructure-control-plane](../class-diagrams/svg/90-pkg-infrastructure-control-plane.svg)

### Описание

Диаграмма «Package Family: infrastructure/control_plane» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/control_plane; modules: file_effective_config_artifact_store, file_lineage_store, file_run_ledger_store, file_run_manifest_store.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: file effective config artifact store, file lineage store, file run ledger store, file run manifest store. Показательные узлы для быстрого чтения: FileEffectiveConfigArtifactStore, FileLineageStore, FileRunLedgerStore, FileRunManifestStore. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-04-02`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-export

**Package Family: infrastructure/export**

![90-pkg-infrastructure-export](../class-diagrams/svg/90-pkg-infrastructure-export.svg)

### Описание

Диаграмма «Package Family: infrastructure/export» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/export; modules: csv_exporter, dq_report_writer, export_catalog_adapter, export_writer_adapter.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: csv exporter, dq report writer, export catalog adapter, export writer adapter. Показательные узлы для быстрого чтения: CsvExporter, DQReportWriter, ExportCatalogAdapter, ExportWriterAdapter. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-observability-anomaly

**Package Family: infrastructure/observability/anomaly**

![90-pkg-infrastructure-observability-anomaly](../class-diagrams/svg/90-pkg-infrastructure-observability-anomaly.svg)

### Описание

Диаграмма «Package Family: infrastructure/observability/anomaly» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/observability/anomaly; modules: types, detector, monitor.. Схема имеет плотность порядка 5 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: types, detector, monitor. Показательные узлы для быстрого чтения: AnomalyRecord, AnomalySeverity, AnomalyType, AnomalyDetector, DataQualityMonitorService. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-schemas-part1

**Package Family: infrastructure/schemas (Part 1/3)**

![90-pkg-infrastructure-schemas-part1](../class-diagrams/svg/90-pkg-infrastructure-schemas-part1.svg)

### Описание

Диаграмма «Package Family: infrastructure/schemas (Part 1/3)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/schemas; part 1/3; modules: pipeline_config_common_schemas, base_schemas_chembl, composite_validation.. Схема имеет плотность порядка 29 узлов и 1 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: pipeline config common schemas, base schemas chembl, composite validation. Показательные узлы для быстрого чтения: ContentHashConfig, FilterColumnSchema, GoldColumnFilterConfig, GoldFiltersConfig, GoldListContainsFilterConfig, GoldListLengthFilterConfig. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-schemas-part2

**Package Family: infrastructure/schemas (Part 2/3)**

![90-pkg-infrastructure-schemas-part2](../class-diagrams/svg/90-pkg-infrastructure-schemas-part2.svg)

### Описание

Диаграмма «Package Family: infrastructure/schemas (Part 2/3)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/schemas; part 2/3; modules: base_schemas_pubchem, pipeline_config_common, dq_report_config, source_config.. Схема имеет плотность порядка 26 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: base schemas pubchem, pipeline config common, dq report config, source config. Показательные узлы для быстрого чтения: BaseFilterColumnSchema, BaseGoldColumnFilterConfig, BaseGoldFiltersConfig, BaseGoldListContainsFilterConfig, BaseGoldListLengthFilterConfig, BaseGoldRangeFilterConfig. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `26`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-schemas-part3

**Package Family: infrastructure/schemas (Part 3/3)**

![90-pkg-infrastructure-schemas-part3](../class-diagrams/svg/90-pkg-infrastructure-schemas-part3.svg)

### Описание

Диаграмма «Package Family: infrastructure/schemas (Part 3/3)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/schemas; part 3/3; modules: composite_config_base, pipeline_config_provider, \_composite_config_merge_schema, filter_config, dq_config, composite_config.. Схема имеет плотность порядка 25 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: composite config base, pipeline config provider, composite config merge schema, filter config, dq config, composite config. Показательные узлы для быстрого чтения: AggregationFieldSchema, AggregationSchema, DependencySchema, EnricherSchema, SeedSchema, ApiConfig. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-bronze

**Package Family: infrastructure/storage/bronze**

![90-pkg-infrastructure-storage-bronze](../class-diagrams/svg/90-pkg-infrastructure-storage-bronze.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/bronze» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/storage/bronze; modules: pipeline_helpers, metadata_operations, metadata_builders, metrics_mixin, reporting_helpers, io_mixin.. Схема имеет плотность порядка 18 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: pipeline helpers, metadata operations, metadata builders, metrics mixin, reporting helpers, io mixin. Показательные узлы для быстрого чтения: BronzeWriteArtifacts, BronzeWritePostwriteContext, BronzeWritePrepared, BronzeWriteRequest, \_BronzeWritePreparationHostProtocol, BronzeMetadataWriteRequest. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-delta

**Package Family: infrastructure/storage/delta**

![90-pkg-infrastructure-storage-delta](../class-diagrams/svg/90-pkg-infrastructure-storage-delta.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/delta» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/storage/delta; modules: arrow_converter, resilience.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: arrow converter, resilience. Показательные узлы для быстрого чтения: ArrowDataConverter, ArrowSchemaPreparationContext, AdaptiveRetryPolicy, SilverMergeResiliencePolicy. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-gold-part1

**Package Family: infrastructure/storage/gold (Part 1/2)**

![90-pkg-infrastructure-storage-gold-part1](../class-diagrams/svg/90-pkg-infrastructure-storage-gold-part1.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/gold (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/storage/gold; part 1/2; modules: io_delta_runtime, io_mixin, pipeline_helpers, metadata_operations, io_delta_mixins.. Схема имеет плотность порядка 29 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: io delta runtime, io mixin, pipeline helpers, metadata operations, io delta mixins. Показательные узлы для быстрого чтения: \_GoldWriteAsyncioProtocol, \_GoldWriteRetryModuleProtocol, \_GoldWriterDeltaModuleProtocol, \_GoldWriterScd2HostProtocol, \_GoldWriterSimpleDeltaHostProtocol, \_PreparedScd2GoldWrite. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-gold-part2

**Package Family: infrastructure/storage/gold (Part 2/2)**

![90-pkg-infrastructure-storage-gold-part2](../class-diagrams/svg/90-pkg-infrastructure-storage-gold-part2.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/gold (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/storage/gold; part 2/2; modules: metadata_audit, validation_mixin, io_helpers, metadata_mixin, read_cleanup_mixin, runtime_helpers.. Схема имеет плотность порядка 8 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: metadata audit, validation mixin, io helpers, metadata mixin, read cleanup mixin, runtime helpers. Показательные узлы для быстрого чтения: \_GoldAuditWriteRequest, \_GoldMetadataAuditHostProtocol, GoldWriterValidationMixin, \_RunInExecutorHost, \_GoldWriterSCDHostProtocol, GoldWriterMetadataMixin. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `8`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-metadata

**Package Family: infrastructure/storage/metadata**

![90-pkg-infrastructure-storage-metadata](../class-diagrams/svg/90-pkg-infrastructure-storage-metadata.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/metadata» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/storage/metadata; modules: writer_operations, builder_base.. Схема имеет плотность порядка 8 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: writer operations, builder base. Показательные узлы для быстрого чтения: \_MetadataWriteFinalTelemetry, \_MetadataWriteRequest, \_MetadataWriteRetryState, \_MetadataWriteTelemetryContext, \_PreparedMetadataWrite, \_PreparedMetadataWriteOperation. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `8`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-silver-part1

**Package Family: infrastructure/storage/silver (Part 1/2)**

![90-pkg-infrastructure-storage-silver-part1](../class-diagrams/svg/90-pkg-infrastructure-storage-silver-part1.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/silver (Part 1/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/storage/silver; part 1/2; modules: metadata_operations, pipeline_helpers, validation_operations, delta_helpers, merged_operations, postwrite_mixin.. Схема имеет плотность порядка 29 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: metadata operations, pipeline helpers, validation operations, delta helpers, merged operations, postwrite mixin. Показательные узлы для быстрого чтения: \_PreparedSilverMetadataWriteOperation, \_PreparedSilverWriteFinalizationContext, \_ResolvedSilverMetadataContext, \_SilverMergedMetadataWriteRequest, \_SilverMetadataWriteHostProtocol, \_SilverMetadataWriteRequest. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `29`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-silver-part2

**Package Family: infrastructure/storage/silver (Part 2/2)**

![90-pkg-infrastructure-storage-silver-part2](../class-diagrams/svg/90-pkg-infrastructure-storage-silver-part2.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/silver (Part 2/2)» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory slice for src/bioetl/infrastructure/storage/silver; part 2/2; modules: audit_operations, merged_mixin, schema_drift_operations, delta_mixin, maintenance_mixin, metadata_mixin.. Схема имеет плотность порядка 11 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: audit operations, merged mixin, schema drift operations, delta mixin, maintenance mixin, metadata mixin. Показательные узлы для быстрого чтения: \_SilverAuditHostProtocol, \_SilverAuditWriteRequest, SilverWriterMergedMixin, \_MergedSilverMetadataWriterProtocol, \_SchemaDriftHostProtocol, \_SilverSchemaDriftDiff. Примечание: Generated supplemental package-family slice used to keep node density within the class-diagram readability budget (\<= 30)..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-storage-support

**Package Family: infrastructure/storage/support**

![90-pkg-infrastructure-storage-support](../class-diagrams/svg/90-pkg-infrastructure-storage-support.svg)

### Описание

Диаграмма «Package Family: infrastructure/storage/support» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/storage/support; modules: atomic_ops, checkpoint_writer, retention.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: atomic ops, checkpoint writer, retention. Показательные узлы для быстрого чтения: AtomicWriteError, AtomicWriteGroup, FileCompositeCheckpointWriter, RetentionPolicy. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-infrastructure-validation

**Package Family: infrastructure/validation**

![90-pkg-infrastructure-validation](../class-diagrams/svg/90-pkg-infrastructure-validation.svg)

### Описание

Диаграмма «Package Family: infrastructure/validation» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/infrastructure/validation; modules: pandera_validator, contract_validator.. Схема имеет плотность порядка 6 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: pandera validator, contract validator. Показательные узлы для быстрого чтения: BasePanderaValidator, NoOpValidator, PanderaGoldValidator, PanderaSilverValidator, ContractAwareGoldValidator, ContractAwareSilverValidator. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-interfaces-cli-commands-domains-quarantine

**Package Family: interfaces/cli/commands/domains/quarantine**

![90-pkg-interfaces-cli-commands-domains-quarantine](../class-diagrams/svg/90-pkg-interfaces-cli-commands-domains-quarantine.svg)

### Описание

Диаграмма «Package Family: interfaces/cli/commands/domains/quarantine» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/interfaces/cli/commands/domains/quarantine; modules: support, execution.. Схема имеет плотность порядка 4 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: support, execution. Показательные узлы для быстрого чтения: \_QuarantineCommandContext, \_QuarantineManager, \_QuarantineService, QuarantineExecutionPolicy. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-interfaces-cli-commands-domains-run-all

**Package Family: interfaces/cli/commands/domains/run_all**

![90-pkg-interfaces-cli-commands-domains-run-all](../class-diagrams/svg/90-pkg-interfaces-cli-commands-domains-run-all.svg)

### Описание

Диаграмма «Package Family: interfaces/cli/commands/domains/run_all» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/interfaces/cli/commands/domains/run_all; modules: command_policy, support, execution.. Схема имеет плотность порядка 16 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: command policy, support, execution. Показательные узлы для быстрого чтения: BatchExecutorCallable, BatchExitCodeCallable, BatchSummaryPresenterCallable, DestructiveConfirmationCallable, ExitCallable, HealthInfoPresenterCallable. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-interfaces-cli-commands-domains-run

**Package Family: interfaces/cli/commands/domains/run**

![90-pkg-interfaces-cli-commands-domains-run](../class-diagrams/svg/90-pkg-interfaces-cli-commands-domains-run.svg)

### Описание

Диаграмма «Package Family: interfaces/cli/commands/domains/run» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/interfaces/cli/commands/domains/run; modules: command_policy.. Схема имеет плотность порядка 6 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: command policy. Показательные узлы для быстрого чтения: ExitCallable, HealthInfoPresenterCallable, ResultFinalizerCallable, ResultPresenterCallable, RunCommandInput, RunExecutorCallable. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 90-pkg-interfaces-http

**Package Family: interfaces/http**

![90-pkg-interfaces-http](../class-diagrams/svg/90-pkg-interfaces-http.svg)

### Описание

Диаграмма «Package Family: interfaces/http» показывает архитектурную модель модуля и фиксирует контракты, роли и отношения между сущностями слоя. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Package Family / Inventory Slice». В комментариях исходника зафиксирован фокус диаграммы: AST-derived supplemental package-family inventory for src/bioetl/interfaces/http; modules: health_server_routing_mixin, health_server_http_mixin, health_server, health_server_state_mixin, types.. Схема имеет плотность порядка 8 узлов и 3 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: health server routing mixin, health server http mixin, health server, health server state mixin, types. Показательные узлы для быстрого чтения: HealthServerRoutingMixin, \_HealthResponseSupport, \_HealthStateSupport, HealthServerHTTPMixin, \_RouteRequestSupport, HealthServer. Примечание: Generated supplemental package-family diagram. Curated class-summary remains narrative-only..

### Метаданные

- Тип: `classDiagram`
- Уровень: `Package Family / Inventory Slice`
- Дата: `2026-03-27`
- Узлы (metadata): `8`
