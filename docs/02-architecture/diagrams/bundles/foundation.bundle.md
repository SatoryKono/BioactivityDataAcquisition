# BioETL Foundation Diagrams Bundle

- Generated: 2026-04-13T12:35:15
- Diagram count: 55

## Table of Contents

- [01-full-system-component — Full System Component Diagram](#01-full-system-component)
- [01-high-level — High-Level System Architecture](#01-high-level)
- [02-full-medallion-data-flow — Full Medallion Data Flow with Lineage and DQ](#02-full-medallion-data-flow)
- [03-pipeline-execution-happy-path — Pipeline Execution — Happy Path](#03-pipeline-execution-happy-path)
- [04-domain-layer-class-diagram — Domain Layer Class Diagram](#04-domain-layer-class-diagram)
- [04-error-flow — Error Handling and Quarantine Flow](#04-error-flow)
- [05-layers-interaction — Layer Interaction — Hexagonal Runtime Topology](#05-layers-interaction)
- [05-pipeline-lifecycle-states — Pipeline Lifecycle State Machine](#05-pipeline-lifecycle-states)
- [06-application-layer-class-diagram — Application Layer Class Diagram](#06-application-layer-class-diagram)
- [06-pipeline-execution — Pipeline Execution Sequence — Runner to Postrun](#06-pipeline-execution)
- [07-circuit-breaker-states — Circuit Breaker State Machine](#07-circuit-breaker-states)
- [07-medallion-flow — Medallion Data Flow (Sources → Bronze → Silver → Gold)](#07-medallion-flow)
- [08-complete-etl-workflow — Complete ETL Workflow (6 Phases)](#08-complete-etl-workflow)
- [08-domain-ddd — Domain Layer — DDD Components](#08-domain-ddd)
- [09-full-er-diagram — Entity-Relationship Diagram (All Providers)](#09-full-er-diagram)
- [10-infrastructure-layer-class-diagram — Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram)
- [11-lock-acquisition-sequence — Lock Acquisition Sequence (Two Workers)](#11-lock-acquisition-sequence)
- [12-local-deployment-architecture — Local Deployment Architecture](#12-local-deployment-architecture)
- [13-domain-models-relationship — Domain Models Relationship Hierarchy](#13-domain-models-relationship)
- [14-provider-health-states — Provider Health State Machine](#14-provider-health-states)
- [15-dq-check-workflow — Data Quality Check Workflow](#15-dq-check-workflow)
- [16-memory-lock-class — MemoryLock Class Diagram](#16-memory-lock-class)
- [17-pipeline-hierarchy — Pipeline and Transformer Class Hierarchy](#17-pipeline-hierarchy)
- [18-bronze-write-sequence — Bronze Write Sequence (JSONL + zstd)](#18-bronze-write-sequence)
- [19-delta-lake-write-sequence — Delta Lake Write Sequence (Silver Layer)](#19-delta-lake-write-sequence)
- [20-quarantine-record-states — Quarantine Record State Machine](#20-quarantine-record-states)
- [21-activity-entity-data-flow — Activity Entity Data Flow (Extract → Transform → Load)](#21-activity-entity-data-flow)
- [22-client-api-request-sequence — HTTP Client API Request Sequence](#22-client-api-request-sequence)
- [23-silver-writer-class — SilverWriter Class Diagram](#23-silver-writer-class)
- [24-hash-service-class — ContentHashService Class Diagram](#24-hash-service-class)
- [25-circuit-breaker-observer-class — Circuit Breaker and Observer Classes](#25-circuit-breaker-observer-class)
- [26-hexagonal-ports-adapters — Hexagonal Architecture — Ports and Adapters Overview](#26-hexagonal-ports-adapters)
- [27-import-matrix-enforcement — Five-Layer Import Matrix Enforcement (ARCH-001)](#27-import-matrix-enforcement)
- [28-composition-root-di-graph — Composition Root Wiring — Public APIs and Assembly](#28-composition-root-di-graph)
- [29-composite-pipeline-workflow — Composite Pipeline Full Workflow — Seed to Gold (ADR-026)](#29-composite-pipeline-workflow)
- [30-port-adapter-mapping — Port-to-Adapter Mapping Table Diagram](#30-port-adapter-mapping)
- [31-pipeline-run-lifecycle — Pipeline Run Lifecycle — From Config to Completion](#31-pipeline-run-lifecycle)
- [32-single-record-journey — Record Processing Pipeline — Single Record Journey](#32-single-record-journey)
- [33-cli-run-interaction — CLI Run Command → Current Execution Flow](#33-cli-run-interaction)
- [34-batch-processing-flow — Batch Processing Flow — BatchProcessingService choreography](#34-batch-processing-flow)
- [35-bootstrap-sequence — Composition Layer Bootstrap Sequence](#35-bootstrap-sequence)
- [36-architecture-principles-mindmap — Architecture Principles Mind Map](#36-architecture-principles-mindmap)
- [37-cli-entry-full-chain — CLI Entry Point to Pipeline and Inspection Chains](#37-cli-entry-full-chain)
- [38-runtime-assembly-sequence — Runtime Assembly Sequence — build_pipeline_runner to PipelineRunner](#38-runtime-assembly-sequence)
- [39-medallion-invariants — Medallion Architecture Invariants (ARCH-007)](#39-medallion-invariants)
- [40-application-core-collaboration — Application Core Component Collaboration](#40-application-core-collaboration)
- [41-error-classification-tree — Error Classification Decision Tree — Full Logic](#41-error-classification-tree)
- [42-pipeline-runner-class — PipelineRunner Collaborator Diagram](#42-pipeline-runner-class)
- [43-fan-out-fan-in-pattern — Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment](#43-fan-out-fan-in-pattern)
- [44-cross-provider-enrichment — Cross-Provider Data Enrichment Flow — Publication](#44-cross-provider-enrichment)
- [46-yaml-config-resolution — YAML Configuration and Contract Rollout Resolution Chain](#46-yaml-config-resolution)
- [47-publication-merge-sources — Publication Composite — Merge All Sources](#47-publication-merge-sources)
- [48-composite-phase-lifecycle — Composite Pipeline Phase Lifecycle and Resume Semantics](#48-composite-phase-lifecycle)
- [49-composite-runner-class — CompositePipelineRunner — Component Diagram](#49-composite-runner-class)
- [50-exception-hierarchy — Exception Hierarchy — Full Tree](#50-exception-hierarchy)

\\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component

**Full System Component Diagram**

![01-full-system-component](../foundation/svg/01-full-system-component.svg)

### Описание

Диаграмма «Full System Component Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Five-Layer Architecture), §1.2 (Ports & Adapters), composition/runtime_builders, application/core. Схема имеет плотность порядка 35 узлов и 49 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Systems, Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: Bioactivity APIs, Publication APIs, CLI run / run-all / run-composite, CLI run-manifest / lineage / checkpoint, Signal orchestration, execution_api. Связанный ADR: ADR-040.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-28`
- Узлы (metadata): `35`
- ADR: `ADR-040`

\\newpage

<div style="page-break-before: always;"></div>

## 01-high-level

**High-Level System Architecture**

![01-high-level](../foundation/svg/01-high-level.svg)

### Описание

Диаграмма «High-Level System Architecture» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Five-Layer Architecture). Схема имеет плотность порядка 20 узлов и 12 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Data Sources, Interfaces Layer, Composition Layer, Application Layer, Infrastructure Layer, Data Lake — Local Storage. Показательные узлы для быстрого чтения: ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API, OpenAlex API.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `20`

\\newpage

<div style="page-break-before: always;"></div>

## 02-full-medallion-data-flow

**Full Medallion Data Flow with Lineage and DQ**

![02-full-medallion-data-flow](../foundation/svg/02-full-medallion-data-flow.svg)

### Описание

Диаграмма «Full Medallion Data Flow with Lineage and DQ» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Medallion Architecture), §2.3 (Quarantine), §3.1 (DQ). Схема имеет плотность порядка 16 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Sources, Bronze Layer, Silver Layer, Gold Layer, Data Quality Branch, Lineage Tracking. Показательные узлы для быстрого чтения: ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API, OpenAlex API.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 03-pipeline-execution-happy-path

**Pipeline Execution — Happy Path**

![03-pipeline-execution-happy-path](../foundation/svg/03-pipeline-execution-happy-path.svg)

### Описание

Диаграмма «Pipeline Execution — Happy Path» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: application/core/runner.py, batch_executor.py, batch_processing_service.py, preflight/service.py, postrun/service.py. Схема имеет плотность порядка 10 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram

**Domain Layer Class Diagram**

![04-domain-layer-class-diagram](../foundation/svg/04-domain-layer-class-diagram.svg)

### Описание

Диаграмма «Domain Layer Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Domain Layer), §1.2 (Ports), §1.3 (Entities). Схема имеет плотность порядка 26 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Ports, Entities, Config, Types. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `26`

\\newpage

<div style="page-break-before: always;"></div>

## 04-error-flow

**Error Handling and Quarantine Flow**

![04-error-flow](../foundation/svg/04-error-flow.svg)

### Описание

Диаграмма «Error Handling and Quarantine Flow» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.1 (Error Classification), §2.3 (Quarantine). Схема имеет плотность порядка 35 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Pipeline Execution, Error Classification (§3.1), Error Handling, Quarantine (§2.3).

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `35`

\\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction

**Layer Interaction — Hexagonal Runtime Topology**

![05-layers-interaction](../foundation/svg/05-layers-interaction.svg)

### Описание

Диаграмма «Layer Interaction — Hexagonal Runtime Topology» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Layers), §1.2 (Ports & Adapters), composition/runtime_builders, application/core. Схема имеет плотность порядка 21 узлов и 29 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Composite Pipeline (ADR-026), Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI commands, PipelineRunnerService, build_pipeline_runner, PipelineRegistry, GenericPipelineFactory, StorageFactory.

### Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `21`

\\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states

**Pipeline Lifecycle State Machine**

![05-pipeline-lifecycle-states](../foundation/svg/05-pipeline-lifecycle-states.svg)

### Описание

Диаграмма «Pipeline Lifecycle State Machine» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Pipeline Execution), §3.5 (Graceful Shutdown). Схема имеет плотность порядка 15 узлов и 65 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram

**Application Layer Class Diagram**

![06-application-layer-class-diagram](../foundation/svg/06-application-layer-class-diagram.svg)

### Описание

Диаграмма «Application Layer Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Application Layer), application/core/, application/services/, application/observability/. Схема имеет плотность порядка 25 узлов и 27 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Core, Services, ControlPlane, Transformers. Показательные узлы для быстрого чтения: BasePipeline, PipelineRunner, PipelineRunnerDependencies, BatchExecutor, BatchProcessingService, BatchTransformer.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-28`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 06-pipeline-execution

**Pipeline Execution Sequence — Runner to Postrun**

![06-pipeline-execution](../foundation/svg/06-pipeline-execution.svg)

### Описание

Диаграмма «Pipeline Execution Sequence — Runner to Postrun» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: application/core/{runner,batch_executor,batch_processing_service}.py, preflight/service.py, postrun/service.py. Схема имеет плотность порядка 13 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states

**Circuit Breaker State Machine**

![07-circuit-breaker-states](../foundation/svg/07-circuit-breaker-states.svg)

### Описание

Диаграмма «Circuit Breaker State Machine» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), ADR-007. Схема имеет плотность порядка 3 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `3`

\\newpage

<div style="page-break-before: always;"></div>

## 07-medallion-flow

**Medallion Data Flow (Sources → Bronze → Silver → Gold)**

![07-medallion-flow](../foundation/svg/07-medallion-flow.svg)

### Описание

Диаграмма «Medallion Data Flow (Sources → Bronze → Silver → Gold)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Medallion Architecture), §2.8 (Transformation). Схема имеет плотность порядка 13 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Sources, Bronze Layer, Silver Layer, Gold Layer, Data Characteristics. Показательные узлы для быстрого чтения: (ChEMBL API ), (PubChem API ), (UniProt API ), (PubMed API ), BronzeWriter, ("JSONL + zstd Append-only 90d retention").

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow

**Complete ETL Workflow (6 Phases)**

![08-complete-etl-workflow](../foundation/svg/08-complete-etl-workflow.svg)

### Описание

Диаграмма «Complete ETL Workflow (6 Phases)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: application/core/{runner,batch_executor,batch_processing_service,postrun/service}.py, application/services/medallion_lifecycle.py. Схема имеет плотность порядка 25 узлов и 28 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Phase 1: Startup, Phase 2: Extract, Phase 3: Bronze + Transform, Phase 4: Silver / Gold Load, Phase 5: Postrun, Phase 6: Cleanup. Показательные узлы для быстрого чтения: Enter services + lock contexts, validate_infrastructure, prepare_for_run, load checkpoint / resolve offset, BatchExecutor.execute, extract_records via DataSourcePort.fetch.

### Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `25`

\\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd

**Domain Layer — DDD Components**

![08-domain-ddd](../foundation/svg/08-domain-ddd.svg)

### Описание

Диаграмма «Domain Layer — DDD Components» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Domain Layer), §1.3 (DDD Aggregates), ADR-021. Схема имеет плотность порядка 24 узлов и 17 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer (DDD), ports/, aggregates/, Domain Events, value_objects/, types.py. Показательные узлы для быстрого чтения: Batch Aggregate add_record + quarantine_record seal + mark_committed, PipelineRun Aggregate start + record_stage_success complete + fail, QuarantineEntry Aggregate mark_retrying + mark_recovered mark_dead_letter, RunID (UUID), BatchID (UUID), EntityID (str).

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `24`

\\newpage

<div style="page-break-before: always;"></div>

## 09-full-er-diagram

**Entity-Relationship Diagram (All Providers)**

![09-full-er-diagram](../foundation/svg/09-full-er-diagram.svg)

### Описание

Диаграмма «Entity-Relationship Diagram (All Providers)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате ER-диаграмма и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.3 (Domain Entities), §4 (Provider Specs). Схема имеет плотность порядка 14 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `erDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram

**Infrastructure Layer Class Diagram**

![10-infrastructure-layer-class-diagram](../foundation/svg/10-infrastructure-layer-class-diagram.svg)

### Описание

Диаграмма «Infrastructure Layer Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Infrastructure Layer), §3.6 (Resilience), RF-014. Схема имеет плотность порядка 18 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: HTTP Infrastructure, DataSource Adapters, Storage Writers, Coordination, Observability. Показательные узлы для быстрого чтения: UnifiedHTTPClient, CircuitBreaker, TokenBucket, ChemblAdapter, PubchemAdapter, UniprotAdapter.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-19`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 11-lock-acquisition-sequence

**Lock Acquisition Sequence (Two Workers)**

![11-lock-acquisition-sequence](../foundation/svg/11-lock-acquisition-sequence.svg)

### Описание

Диаграмма «Lock Acquisition Sequence (Two Workers)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.3 (Locking), ADR-010. Схема имеет плотность порядка 5 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture

**Local Deployment Architecture**

![12-local-deployment-architecture](../foundation/svg/12-local-deployment-architecture.svg)

### Описание

Диаграмма «Local Deployment Architecture» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: local-only runtime, in-process locking, local filesystem outputs. Схема имеет плотность порядка 13 узлов и 12 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Local Machine (Single Instance), CLI Execution, Local Pipeline Workers, In-Process Locking, Local filesystem (data/), Local Observability. Показательные узлы для быстрого чтения: 🌐 Provider APIs ChEMBL + PubChem + UniProt + PubMed, 🖥️ CLI / Manual run PipelineRunner, ⏰ Local scheduler (cron/systemd), 📦 Local pipelines chembl\_\* + pubchem_compound + uniprot_protein, MemoryLock in-process only no cross-process coordination, ("📁 bronze/ JSONL+zstd").

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-16`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 13-domain-models-relationship

**Domain Models Relationship Hierarchy**

![13-domain-models-relationship](../foundation/svg/13-domain-models-relationship.svg)

### Описание

Диаграмма «Domain Models Relationship Hierarchy» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.3 (Domain Entities), §1.1 (Domain Layer). Схема имеет плотность порядка 15 узлов и 24 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BaseEntity, Activity, Assay, Target, Molecule, PublicationEntityBase.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states

**Provider Health State Machine**

![14-provider-health-states](../foundation/svg/14-provider-health-states.svg)

### Описание

Диаграмма «Provider Health State Machine» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), §4 (Provider Specifications). Схема имеет плотность порядка 4 узлов и 22 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `4`

\\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow

**Data Quality Check Workflow**

![15-dq-check-workflow](../foundation/svg/15-dq-check-workflow.svg)

### Описание

Диаграмма «Data Quality Check Workflow» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.1 (DQ Checks), §2.3 (Quarantine). Схема имеет плотность порядка 26 узлов и 29 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Input Stage, Validation Stage, Error Classification, Action Paths, Record Routing, Metrics Export. Показательные узлы для быстрого чтения: /"📥 Input Records (from Bronze)"/, 🔍 Pandera Schema Validation, Check required fields, Validate data types, Check value constraints, Validate relationships.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `26`

\\newpage

<div style="page-break-before: always;"></div>

## 16-memory-lock-class

**MemoryLock Class Diagram**

![16-memory-lock-class](../foundation/svg/16-memory-lock-class.svg)

### Описание

Диаграмма «MemoryLock Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.3 (Locking), ADR-010. Схема имеет плотность порядка 7 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: LockPort, MemoryLock, LockEntry, LockResult, LockNotHeldError, LockCoordinator.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 17-pipeline-hierarchy

**Pipeline and Transformer Class Hierarchy**

![17-pipeline-hierarchy](../foundation/svg/17-pipeline-hierarchy.svg)

### Описание

Диаграмма «Pipeline and Transformer Class Hierarchy» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Pipeline Execution), §2.8 (Transformation). Схема имеет плотность порядка 14 узлов и 13 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: BasePipeline, BaseTransformer, BaseChemblTransformer, ActivityTransformer, MoleculeTransformer, AssayTransformer.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 18-bronze-write-sequence

**Bronze Write Sequence (JSONL + zstd)**

![18-bronze-write-sequence](../foundation/svg/18-bronze-write-sequence.svg)

### Описание

Диаграмма «Bronze Write Sequence (JSONL + zstd)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Bronze Layer), §2.2 (Append-Only), application/core batch processing. Схема имеет плотность порядка 7 узлов и 7 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-24`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 19-delta-lake-write-sequence

**Delta Lake Write Sequence (Silver Layer)**

![19-delta-lake-write-sequence](../foundation/svg/19-delta-lake-write-sequence.svg)

### Описание

Диаграмма «Delta Lake Write Sequence (Silver Layer)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Silver Layer), §2.5 (ACID via Delta Lake), silver writer orchestration. Схема имеет плотность порядка 7 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-24`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 20-quarantine-record-states

**Quarantine Record State Machine**

![20-quarantine-record-states](../foundation/svg/20-quarantine-record-states.svg)

### Описание

Диаграмма «Quarantine Record State Machine» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.3 (Quarantine), §3.1 (Error Classification). Схема имеет плотность порядка 6 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `6`

\\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow

**Activity Entity Data Flow (Extract → Transform → Load)**

![21-activity-entity-data-flow](../foundation/svg/21-activity-entity-data-flow.svg)

### Описание

Диаграмма «Activity Entity Data Flow (Extract → Transform → Load)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.8 (Transformation), §4.1 (ChEMBL Activity). Схема имеет плотность порядка 31 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External API, Extract Phase, Transform Phase, Validate Phase, Load Phase, Related Entities (Silver). Показательные узлы для быстрого чтения: 🌐 ChEMBL API /activities endpoint, 📥 Fetch activity_id batch (ChemblAdapter), 🔗 Fetch related entities assay_id, molecule_id, target_id, 💾 Write Bronze JSONL + zstd, 📊 Record Lineage batch_id, paths, 🔧 Normalize units nM → μM standardization.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `31`

\\newpage

<div style="page-break-before: always;"></div>

## 22-client-api-request-sequence

**HTTP Client API Request Sequence**

![22-client-api-request-sequence](../foundation/svg/22-client-api-request-sequence.svg)

### Описание

Диаграмма «HTTP Client API Request Sequence» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), §3.7 (Rate Limiting), UnifiedHTTPClient retry flow. Схема имеет плотность порядка 7 узлов и 15 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-24`
- Узлы (metadata): `7`

\\newpage

<div style="page-break-before: always;"></div>

## 23-silver-writer-class

**SilverWriter Class Diagram**

![23-silver-writer-class](../foundation/svg/23-silver-writer-class.svg)

### Описание

Диаграмма «SilverWriter Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Silver Layer), §2.5 (ACID via Delta Lake), RF-010, RF-014. Схема имеет плотность порядка 9 узлов и 5 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: SilverStoragePort, MergedStoragePort, StorageMaintenancePort, SilverWriter, SilverWriterRuntimeServices, WriteModePolicy.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-19`
- Узлы (metadata): `9`

\\newpage

<div style="page-break-before: always;"></div>

## 24-hash-service-class

**ContentHashService Class Diagram**

![24-hash-service-class](../foundation/svg/24-hash-service-class.svg)

### Описание

Диаграмма «ContentHashService Class Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.4 (Deduplication via content_hash). Схема имеет плотность порядка 5 узлов и 4 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: ContentHashService, NormalizationRules, ContentHash, BaseTransformer, HashFlow.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `5`

\\newpage

<div style="page-break-before: always;"></div>

## 25-circuit-breaker-observer-class

**Circuit Breaker and Observer Classes**

![25-circuit-breaker-observer-class](../foundation/svg/25-circuit-breaker-observer-class.svg)

### Описание

Диаграмма «Circuit Breaker and Observer Classes» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), ADR-007. Схема имеет плотность порядка 8 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: CircuitState, CircuitBreakerPort, CircuitBreaker, CircuitBreakerMetrics, CircuitBreakerConfig, CircuitOpenError.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `8`

\\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters

**Hexagonal Architecture — Ports and Adapters Overview**

![26-hexagonal-ports-adapters](../foundation/svg/26-hexagonal-ports-adapters.svg)

### Описание

Диаграмма «Hexagonal Architecture — Ports and Adapters Overview» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.2 (Ports & Adapters), §1.1 (Five-Layer Architecture). Схема имеет плотность порядка 35 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Layer — Ports (Protocol), Data Ports, Coordination Ports, Observability Ports, Quality & Security Ports, Metadata & Config Ports. Показательные узлы для быстрого чтения: DataSourcePort • fetch() → AsyncIterator • health_check() → HealthStatus, FilterableDataSourcePort • fetch_filtered(), StoragePort • write_bronze() • write_silver() • write_gold(), DeltaReaderPort • read_table() • get_schema(), LockPort • acquire() • release() • renew(), CheckpointPort • save() • load() • delete().

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `35`

\\newpage

<div style="page-break-before: always;"></div>

## 27-import-matrix-enforcement

**Five-Layer Import Matrix Enforcement (ARCH-001)**

![27-import-matrix-enforcement](../foundation/svg/27-import-matrix-enforcement.svg)

### Описание

Диаграмма «Five-Layer Import Matrix Enforcement (ARCH-001)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1, ai-selfreview-rules.md ARCH-001. Схема имеет плотность порядка 11 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Legend, BioETL Five-Layer Architecture, Enforcement Mechanism. Показательные узлы для быстрого чтения: ✅ Allowed Import, ❌ Forbidden Import, Interfaces Layer CLI (Click), HealthServer src/bioetl/interfaces/, Composition Layer Factories + registries src/bioetl/composition/, Application Layer Runner + executor + services src/bioetl/application/, Domain Layer Ports + entities + types src/bioetl/domain/.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph

**Composition Root Wiring — Public APIs and Assembly**

![28-composition-root-di-graph](../foundation/svg/28-composition-root-di-graph.svg)

### Описание

Диаграмма «Composition Root Wiring — Public APIs and Assembly» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Module)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Composition Layer), ADR-005, RF-011. Схема имеет плотность порядка 23 узлов и 28 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Interfaces, Public composition APIs, Composition assembly, Created runtime objects. Показательные узлы для быстрого чтения: CLI / interfaces layer, execution_api runner creation + metrics flush, services_api service accessors, resources_api cleanup / checkpoint / archive helpers, creation_api compat shim → creation_support, entrypoints.py retained broad facade.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Module)`
- Дата: `2026-03-28`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow

**Composite Pipeline Full Workflow — Seed to Gold (ADR-026)**

![29-composite-pipeline-workflow](../foundation/svg/29-composite-pipeline-workflow.svg)

### Описание

Диаграмма «Composite Pipeline Full Workflow — Seed to Gold (ADR-026)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: application/composite runner, checkpoint snapshot + ledger replay, runtime bootstrap. Схема имеет плотность порядка 19 узлов и 38 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Phase 1: Initialization, Phase 2: Seed Pipeline, Phase 3: Dependencies, Phase 3.5: Key Extraction, Phase 4: Fan-Out Enrichment, Phase 5: Merge. Показательные узлы для быстрого чтения: [S] Load CompositeConfig from YAML, [S] Run seed PipelineRunner (e.g., chembl_publication), ("\[D, [S] DependencyCoordinatorService • run_dependencies(), ("\[D, [S] KeyExtractorService • extract_keys(seed_silver, join_keys=[doi, pmid]).

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-04-02`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping

**Port-to-Adapter Mapping Table Diagram**

![30-port-adapter-mapping](../foundation/svg/30-port-adapter-mapping.svg)

### Описание

Диаграмма «Port-to-Adapter Mapping Table Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.2 (Ports & Adapters), ARCH-008 (Single Source). Схема имеет плотность порядка 35 узлов и 79 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Domain Ports (domain/ports/), Core Data & State, Observability & DQ, Validation & Policy, Runtime Controls, Infrastructure Adapters. Показательные узлы для быстрого чтения: [P] DataSourcePort, [P] FilterableDataSourcePort, [P] StoragePort, [P] LockPort, [P] CheckpointPort, [P] QuarantinePort.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-27`
- Узлы (metadata): `35`

\\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle

**Pipeline Run Lifecycle — From Config to Completion**

![31-pipeline-run-lifecycle](../foundation/svg/31-pipeline-run-lifecycle.svg)

### Описание

Диаграмма «Pipeline Run Lifecycle — From Config to Completion» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Execution), domain/aggregates/pipeline_run.py. Схема имеет плотность порядка 1 узлов и 30 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `1`

\\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey

**Record Processing Pipeline — Single Record Journey**

![32-single-record-journey](../foundation/svg/32-single-record-journey.svg)

### Описание

Диаграмма «Record Processing Pipeline — Single Record Journey» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: application/core/{batch_processing_service,batch_processing_support,batch_transformer,batch_writer}.py. Схема имеет плотность порядка 19 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: 1. Source Record, 2. Bronze Capture, 3. Transform Record, 4. DQ + Route, 5. Persist Outputs. Показательные узлы для быстрого чтения: Provider response raw BronzeRecord bytes, DataSourcePort.fetch() yield BronzeRecord, BatchProcessingService.process_batch() batch_id + source metadata, write_bronze_layer() BatchWriter.write_bronze(), ("Bronze file / manifest bronze/.../batch\_\*.jsonl.zst"), BatchTransformer.transform_batch().

### Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction

**CLI Run Command → Current Execution Flow**

![33-cli-run-interaction](../foundation/svg/33-cli-run-interaction.svg)

### Описание

Диаграмма «CLI Run Command → Current Execution Flow» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Module)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Interfaces → Composition → Application), RF-011. Схема имеет плотность порядка 10 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Module)`
- Дата: `2026-03-19`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow

**Batch Processing Flow — BatchProcessingService choreography**

![34-batch-processing-flow](../foundation/svg/34-batch-processing-flow.svg)

### Описание

Диаграмма «Batch Processing Flow — BatchProcessingService choreography» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Data Flow), application/core/{batch_executor,batch_processing_service,batch_processing_support}.py. Схема имеет плотность порядка 14 узлов и 6 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `14`

\\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence

**Composition Layer Bootstrap Sequence**

![35-bootstrap-sequence](../foundation/svg/35-bootstrap-sequence.svg)

### Описание

Диаграмма «Composition Layer Bootstrap Sequence» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Composition Root), composition/bootstrap/runtime/. Схема имеет плотность порядка 28 узлов и 27 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Step 1: Logger, Step 2: Configuration, Step 3: Observability Bundle, Step 4: Storage, Step 5: HTTP Client, Step 6: Data Source. Показательные узлы для быстрого чтения: BootstrapLogger.configure(), StructlogLogger (JSON, ISO timestamps, run_id binding), ConfigLoader.load(pipeline_name), PipelineYamlConfig (\_base.yaml merged with entity.yaml), DQ + Filter config loaders, ObservabilityBundle.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-24`
- Узлы (metadata): `28`

\\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap

**Architecture Principles Mind Map**

![36-architecture-principles-mindmap](../foundation/svg/36-architecture-principles-mindmap.svg)

### Описание

Диаграмма «Architecture Principles Mind Map» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате интеллект-карта (mindmap) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1 (Architecture), all ADRs. Схема имеет плотность порядка 1 узлов; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `mindmap`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `1`

\\newpage

<div style="page-break-before: always;"></div>

## 37-cli-entry-full-chain

**CLI Entry Point to Pipeline and Inspection Chains**

![37-cli-entry-full-chain](../foundation/svg/37-cli-entry-full-chain.svg)

### Описание

Диаграмма «CLI Entry Point to Pipeline and Inspection Chains» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: interfaces/cli/main.py, interfaces/cli/commands/domains/run/{command,command_policy,runtime_helpers}.py, interfaces/cli/commands/{run_manifest,lineage,checkpoint}.py, application/services/{cli_run_orchestration_service,pipeline_runner_service}.py. Схема имеет плотность порядка 23 узлов и 25 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Interfaces Layer (Click), Run command path, CLI Policy / App Service, Async Runtime Helper, Composition Layer, Application Runtime. Показательные узлы для быстрого чтения: bioetl main group, bioetl run / run-all / run-composite, bioetl run-manifest / lineage, bioetl checkpoint / health / export / quarantine, build_run_command_input() normalized RunCommandInput, run_command_flow().

### Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата: `2026-03-28`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 38-runtime-assembly-sequence

**Runtime Assembly Sequence — build_pipeline_runner to PipelineRunner**

![38-runtime-assembly-sequence](../foundation/svg/38-runtime-assembly-sequence.svg)

### Описание

Диаграмма «Runtime Assembly Sequence — build_pipeline_runner to PipelineRunner» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: composition/runtime_builders/runner_builder.py, runtime_builders/control_plane.py, runtime_builders/ledger_collaborator.py, composition/factories/pipeline/{assembler,factory_method_helpers,\_creation_wiring,runner_assembly}.py, ADR-005. Схема имеет плотность порядка 12 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-28`
- Узлы (metadata): `12`

\\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants

**Medallion Architecture Invariants (ARCH-007)**

![39-medallion-invariants](../foundation/svg/39-medallion-invariants.svg)

### Описание

Диаграмма «Medallion Architecture Invariants (ARCH-007)» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Medallion), ARCH-007 clear policy. Схема имеет плотность порядка 23 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: RunType Enum (domain/types.py), MedallionLifecycleService\\n(application/services/medallion_lifecycle.py), INCREMENTAL Path, BACKFILL Path, REBUILD Path, Enforcement. Показательные узлы для быстрого чтения: RunType.INCREMENTAL 'Fetch new data since last run', RunType.BACKFILL 'Re-fetch a date range', RunType.REBUILD 'Full clean rebuild', ❌ DO NOT clear Silver, ❌ DO NOT clear Gold, Silver: merge/upsert (content_hash dedup).

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 40-application-core-collaboration

**Application Core Component Collaboration**

![40-application-core-collaboration](../foundation/svg/40-application-core-collaboration.svg)

### Описание

Диаграмма «Application Core Component Collaboration» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Application Layer), application/core/. Схема имеет плотность порядка 15 узлов и 19 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: PipelineRunner (application/core/runner.py), Lifecycle Services, Pre/Post Services, Batch Execution, Observability, PipelineService bundle. Показательные узлы для быстрого чтения: run() — main orchestrator, HeartbeatService • start() • stop(), CheckpointManagerService • load_checkpoint() • save_checkpoint(), ShutdownService • is_shutting_down() • initiate_shutdown(), PreflightService • validate_pipeline_config() • validate_provider_health(), PostrunService • run() • run_dq_checks() • run_vacuum_if_enabled().

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-24`
- Узлы (metadata): `15`

\\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree

**Error Classification Decision Tree — Full Logic**

![41-error-classification-tree](../foundation/svg/41-error-classification-tree.svg)

### Описание

Диаграмма «Error Classification Decision Tree — Full Logic» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.1 (Error Handling), domain/exceptions/. Схема имеет плотность порядка 22 узлов и 44 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: HTTP Branch Outcomes, Domain Branch Outcomes, Infrastructure Branch Outcomes, Error Actions. Показательные узлы для быстрого чтения: Error Occurred, [A] RETRY max_attempts: 3 multiplier: 2.0 jitter: MD5-based, [A] FAIL FAST No retry Pipeline terminates ExitCode.PIPELINE_ERROR, [A] BATCH FAIL error_rate > 20% Entire batch rejected Checkpoint NOT saved.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `22`

\\newpage

<div style="page-break-before: always;"></div>

## 42-pipeline-runner-class

**PipelineRunner Collaborator Diagram**

![42-pipeline-runner-class](../foundation/svg/42-pipeline-runner-class.svg)

### Описание

Диаграмма «PipelineRunner Collaborator Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Component / Class». В комментариях исходника зафиксирован фокус диаграммы: application/core/runner.py, application/core/pipeline_services.py, composition/factories/pipeline/runner_assembly.py. Схема имеет плотность порядка 11 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: PipelineRunner, PipelineRunnerDependencies, PipelineService, BatchExecutor, LockCoordinator, PreflightService.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Component / Class`
- Дата: `2026-03-24`
- Узлы (metadata): `11`

\\newpage

<div style="page-break-before: always;"></div>

## 43-fan-out-fan-in-pattern

**Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment**

![43-fan-out-fan-in-pattern](../foundation/svg/43-fan-out-fan-in-pattern.svg)

### Описание

Диаграмма «Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: ADR-026 (Composite Pipeline Pattern), application/composite/. Схема имеет плотность порядка 18 узлов и 17 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Seed Pipeline Result, Key Extraction, Fan-Out (EnrichmentCoordinator), Enricher Silver Tables, Fan-In (MergeService), Gold Output. Показательные узлы для быстрого чтения: ("Seed Silver Table (e.g., chembl/publication ) "), DOI Keys (~50,000 unique), PMID Keys (~30,000 unique), CrossRef Enricher filter_ids = DOIs required = true timeout = 3600s, PubMed Enricher filter_ids = PMIDs required = true timeout = 3600s, OpenAlex Enricher filter_ids = DOIs required = false timeout = 1800s.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `18`

\\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment

**Cross-Provider Data Enrichment Flow — Publication**

![44-cross-provider-enrichment](../foundation/svg/44-cross-provider-enrichment.svg)

### Описание

Диаграмма «Cross-Provider Data Enrichment Flow — Publication» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: ADR-026 (Composite), publication composite pipeline config. Схема имеет плотность порядка 19 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: ChEMBL (Seed), CrossRef (Enricher), PubMed (Enricher), OpenAlex (Enricher), Semantic Scholar (Enricher), Merge Phase. Показательные узлы для быстрого чтения: ChemblAdapter /document endpoint, PublicationTransformer, ("Silver chembl/publication" ), CrossRefAdapter /works?filter=doi:..., CrossRefPublicationTransformer, ("Silver crossref/publication" ).

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `19`

\\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution

**YAML Configuration and Contract Rollout Resolution Chain**

![46-yaml-config-resolution](../foundation/svg/46-yaml-config-resolution.svg)

### Описание

Диаграмма «YAML Configuration and Contract Rollout Resolution Chain» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: unified config path, contract rollout policy, and planner/runtime version routing. Схема имеет плотность порядка 23 узлов и 29 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: YAML File Hierarchy, Infrastructure Config Loaders, Domain Config Objects (Frozen), Contract / rollout policy, Pydantic Validation Layer. Показательные узлы для быстрого чтения: configs/base/pipeline.yaml (global defaults), configs/providers/{provider}.yaml (provider defaults), configs/entities/{provider}/{entity}.yaml (unified entity config), configs/providers/{provider}.yaml (source config + legacy-flat fallback), DQ hierarchy base + provider + entity + inline, Filter hierarchy base + provider + entity + inline.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-04-02`
- Узлы (metadata): `23`

\\newpage

<div style="page-break-before: always;"></div>

## 47-publication-merge-sources

**Publication Composite — Merge All Sources**

![47-publication-merge-sources](../foundation/svg/47-publication-merge-sources.svg)

### Описание

Диаграмма «Publication Composite — Merge All Sources» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: application/composite/merger.py, composite/coordinator.py, composite configs. Схема имеет плотность порядка 13 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-16`
- Узлы (metadata): `13`

\\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle

**Composite Pipeline Phase Lifecycle and Resume Semantics**

![48-composite-phase-lifecycle](../foundation/svg/48-composite-phase-lifecycle.svg)

### Описание

Диаграмма «Composite Pipeline Phase Lifecycle and Resume Semantics» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: domain/composite/state.py, checkpoint replay gate, run-ledger stage semantics. Схема имеет плотность порядка 10 узлов и 26 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности.

### Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-04-02`
- Узлы (metadata): `10`

\\newpage

<div style="page-break-before: always;"></div>

## 49-composite-runner-class

**CompositePipelineRunner — Component Diagram**

![49-composite-runner-class](../foundation/svg/49-composite-runner-class.svg)

### Описание

Диаграмма «CompositePipelineRunner — Component Diagram» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: application/composite/ (runner facade, dependency group, checkpoint facade, coordinators). Схема имеет плотность порядка 16 узлов и 12 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: CompositePipelineRunner, CompositeRunnerDependencyGroup, CompositeConfig, CompositeRuntimeConfig, FSMStateHelperService, KeyExtractorService.

### Метаданные

- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-03-28`
- Узлы (metadata): `16`

\\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy

**Exception Hierarchy — Full Tree**

![50-exception-hierarchy](../foundation/svg/50-exception-hierarchy.svg)

### Описание

Диаграмма «Exception Hierarchy — Full Tree» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: domain/exceptions/ (base, network, validation, internal, infrastructure, data_quality). Схема имеет плотность порядка 35 узлов и 48 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: Exception (Python built-in), BioETLError domain/exceptions/base.py error_type: ErrorType context: dict, ErrorClassifier domain/error_classifier.py .classify(error) → ErrorType.

### Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Узлы (metadata): `35`
