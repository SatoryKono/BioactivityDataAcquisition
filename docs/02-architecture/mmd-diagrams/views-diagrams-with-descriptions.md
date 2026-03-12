# BioETL Views Diagrams With Descriptions

- Generated: 2026-03-12T14:16:19
- Diagram count: 162

## Table of Contents

- [00-legend — 00 Legend](#00-legend)
- [01-full-system-component-dataflow — 01 Full System Component](#01-full-system-component-dataflow)
- [01-full-system-component-domain — 01 Full System Component](#01-full-system-component-domain)
- [01-full-system-component-full — Full System Component Diagram](#01-full-system-component-full)
- [01-full-system-component-infra — 01 Full System Component](#01-full-system-component-infra)
- [01-full-system-component-overview — 01 Full System Component](#01-full-system-component-overview)
- [01-high-level-dataflow — 01 High Level](#01-high-level-dataflow)
- [01-high-level-domain — 01 High Level](#01-high-level-domain)
- [01-high-level-full — High-Level System Architecture](#01-high-level-full)
- [01-high-level-infra — 01 High Level](#01-high-level-infra)
- [01-high-level-overview — 01 High Level](#01-high-level-overview)
- [02-medallion-dataflow — 02 Medallion](#02-medallion-dataflow)
- [02-medallion-domain — 02 Medallion](#02-medallion-domain)
- [02-medallion-full — Medallion Architecture Layers](#02-medallion-full)
- [02-medallion-infra — 02 Medallion](#02-medallion-infra)
- [02-medallion-overview — 02 Medallion](#02-medallion-overview)
- [03-medallion-data-flow-full — 03 Medallion Data Flow](#03-medallion-data-flow-full)
- [03-medallion-data-flow-overview — 03 Medallion Data Flow](#03-medallion-data-flow-overview)
- [04-domain-layer-class-diagram-dataflow — 04 Domain Layer Class Diagram](#04-domain-layer-class-diagram-dataflow)
- [04-domain-layer-class-diagram-domain — 04 Domain Layer Class Diagram](#04-domain-layer-class-diagram-domain)
- [04-domain-layer-class-diagram-full — Domain Layer Class Diagram](#04-domain-layer-class-diagram-full)
- [04-domain-layer-class-diagram-infra — 04 Domain Layer Class Diagram](#04-domain-layer-class-diagram-infra)
- [04-domain-layer-class-diagram-overview — 04 Domain Layer Class Diagram](#04-domain-layer-class-diagram-overview)
- [05-layers-interaction-dataflow — 05 Layers Interaction](#05-layers-interaction-dataflow)
- [05-layers-interaction-domain — 05 Layers Interaction](#05-layers-interaction-domain)
- [05-layers-interaction-full — Layer Interaction — Hexagonal Architecture](#05-layers-interaction-full)
- [05-layers-interaction-infra — 05 Layers Interaction](#05-layers-interaction-infra)
- [05-layers-interaction-overview — 05 Layers Interaction](#05-layers-interaction-overview)
- [05-pipeline-lifecycle-states-dataflow — 05 Pipeline Lifecycle States](#05-pipeline-lifecycle-states-dataflow)
- [05-pipeline-lifecycle-states-domain — 05 Pipeline Lifecycle States](#05-pipeline-lifecycle-states-domain)
- [05-pipeline-lifecycle-states-full — Pipeline Lifecycle State Machine](#05-pipeline-lifecycle-states-full)
- [05-pipeline-lifecycle-states-infra — 05 Pipeline Lifecycle States](#05-pipeline-lifecycle-states-infra)
- [05-pipeline-lifecycle-states-overview — 05 Pipeline Lifecycle States](#05-pipeline-lifecycle-states-overview)
- [06-application-layer-class-diagram-dataflow — 06 Application Layer Class Diagram](#06-application-layer-class-diagram-dataflow)
- [06-application-layer-class-diagram-domain — 06 Application Layer Class Diagram](#06-application-layer-class-diagram-domain)
- [06-application-layer-class-diagram-full — Application Layer Class Diagram](#06-application-layer-class-diagram-full)
- [06-application-layer-class-diagram-infra — 06 Application Layer Class Diagram](#06-application-layer-class-diagram-infra)
- [06-application-layer-class-diagram-overview — 06 Application Layer Class Diagram](#06-application-layer-class-diagram-overview)
- [07-circuit-breaker-states-dataflow — 07 Circuit Breaker States](#07-circuit-breaker-states-dataflow)
- [07-circuit-breaker-states-domain — 07 Circuit Breaker States](#07-circuit-breaker-states-domain)
- [07-circuit-breaker-states-full — Circuit Breaker State Machine](#07-circuit-breaker-states-full)
- [07-circuit-breaker-states-infra — 07 Circuit Breaker States](#07-circuit-breaker-states-infra)
- [07-circuit-breaker-states-overview — 07 Circuit Breaker States](#07-circuit-breaker-states-overview)
- [08-complete-etl-workflow-dataflow — 08 Complete Etl Workflow](#08-complete-etl-workflow-dataflow)
- [08-complete-etl-workflow-domain — 08 Complete Etl Workflow](#08-complete-etl-workflow-domain)
- [08-complete-etl-workflow-full — Complete ETL Workflow (6 Phases)](#08-complete-etl-workflow-full)
- [08-complete-etl-workflow-infra — 08 Complete Etl Workflow](#08-complete-etl-workflow-infra)
- [08-complete-etl-workflow-overview — 08 Complete Etl Workflow](#08-complete-etl-workflow-overview)
- [08-domain-ddd-dataflow — 08 Domain Ddd](#08-domain-ddd-dataflow)
- [08-domain-ddd-domain — 08 Domain Ddd](#08-domain-ddd-domain)
- [08-domain-ddd-full — Domain Layer — DDD Components](#08-domain-ddd-full)
- [08-domain-ddd-infra — 08 Domain Ddd](#08-domain-ddd-infra)
- [08-domain-ddd-overview — 08 Domain Ddd](#08-domain-ddd-overview)
- [10-infrastructure-layer-class-diagram-dataflow — 10 Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram-dataflow)
- [10-infrastructure-layer-class-diagram-domain — 10 Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram-domain)
- [10-infrastructure-layer-class-diagram-full — Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram-full)
- [10-infrastructure-layer-class-diagram-infra — 10 Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram-infra)
- [10-infrastructure-layer-class-diagram-overview — 10 Infrastructure Layer Class Diagram](#10-infrastructure-layer-class-diagram-overview)
- [12-local-deployment-architecture-dataflow — 12 Local Deployment Architecture](#12-local-deployment-architecture-dataflow)
- [12-local-deployment-architecture-domain — 12 Local Deployment Architecture](#12-local-deployment-architecture-domain)
- [12-local-deployment-architecture-full — Local Deployment Architecture](#12-local-deployment-architecture-full)
- [12-local-deployment-architecture-infra — 12 Local Deployment Architecture](#12-local-deployment-architecture-infra)
- [12-local-deployment-architecture-overview — 12 Local Deployment Architecture](#12-local-deployment-architecture-overview)
- [13-port-protocol-contracts-full — 13 Port Protocol Contracts](#13-port-protocol-contracts-full)
- [13-port-protocol-contracts-overview — 13 Port Protocol Contracts](#13-port-protocol-contracts-overview)
- [14-provider-health-states-dataflow — 14 Provider Health States](#14-provider-health-states-dataflow)
- [14-provider-health-states-domain — 14 Provider Health States](#14-provider-health-states-domain)
- [14-provider-health-states-full — Provider Health State Machine](#14-provider-health-states-full)
- [14-provider-health-states-infra — 14 Provider Health States](#14-provider-health-states-infra)
- [14-provider-health-states-overview — 14 Provider Health States](#14-provider-health-states-overview)
- [15-dq-check-workflow-dataflow — 15 Dq Check Workflow](#15-dq-check-workflow-dataflow)
- [15-dq-check-workflow-domain — 15 Dq Check Workflow](#15-dq-check-workflow-domain)
- [15-dq-check-workflow-full — Data Quality Check Workflow](#15-dq-check-workflow-full)
- [15-dq-check-workflow-infra — 15 Dq Check Workflow](#15-dq-check-workflow-infra)
- [15-dq-check-workflow-overview — 15 Dq Check Workflow](#15-dq-check-workflow-overview)
- [16-transformer-hierarchy-full — 16 Transformer Hierarchy](#16-transformer-hierarchy-full)
- [16-transformer-hierarchy-overview — 16 Transformer Hierarchy](#16-transformer-hierarchy-overview)
- [21-activity-entity-data-flow-dataflow — 21 Activity Entity Data Flow](#21-activity-entity-data-flow-dataflow)
- [21-activity-entity-data-flow-domain — 21 Activity Entity Data Flow](#21-activity-entity-data-flow-domain)
- [21-activity-entity-data-flow-full — Activity Entity Data Flow (Extract → Transform → Load)](#21-activity-entity-data-flow-full)
- [21-activity-entity-data-flow-infra — 21 Activity Entity Data Flow](#21-activity-entity-data-flow-infra)
- [21-activity-entity-data-flow-overview — 21 Activity Entity Data Flow](#21-activity-entity-data-flow-overview)
- [26-hexagonal-ports-adapters-dataflow — 26 Hexagonal Ports Adapters](#26-hexagonal-ports-adapters-dataflow)
- [26-hexagonal-ports-adapters-domain — 26 Hexagonal Ports Adapters](#26-hexagonal-ports-adapters-domain)
- [26-hexagonal-ports-adapters-full — Hexagonal Architecture — Ports and Adapters Overview](#26-hexagonal-ports-adapters-full)
- [26-hexagonal-ports-adapters-infra — 26 Hexagonal Ports Adapters](#26-hexagonal-ports-adapters-infra)
- [26-hexagonal-ports-adapters-overview — 26 Hexagonal Ports Adapters](#26-hexagonal-ports-adapters-overview)
- [28-composition-root-di-graph-dataflow — 28 Composition Root Di Graph](#28-composition-root-di-graph-dataflow)
- [28-composition-root-di-graph-domain — 28 Composition Root Di Graph](#28-composition-root-di-graph-domain)
- [28-composition-root-di-graph-full — Composition Root Wiring — Full DI Graph](#28-composition-root-di-graph-full)
- [28-composition-root-di-graph-infra — 28 Composition Root Di Graph](#28-composition-root-di-graph-infra)
- [28-composition-root-di-graph-overview — 28 Composition Root Di Graph](#28-composition-root-di-graph-overview)
- [29-composite-pipeline-workflow-dataflow — 29 Composite Pipeline Workflow](#29-composite-pipeline-workflow-dataflow)
- [29-composite-pipeline-workflow-domain — 29 Composite Pipeline Workflow](#29-composite-pipeline-workflow-domain)
- [29-composite-pipeline-workflow-full — Composite Pipeline Full Workflow — Seed to Gold (ADR-026)](#29-composite-pipeline-workflow-full)
- [29-composite-pipeline-workflow-infra — 29 Composite Pipeline Workflow](#29-composite-pipeline-workflow-infra)
- [29-composite-pipeline-workflow-overview — 29 Composite Pipeline Workflow](#29-composite-pipeline-workflow-overview)
- [30-port-adapter-mapping-dataflow — 30 Port Adapter Mapping](#30-port-adapter-mapping-dataflow)
- [30-port-adapter-mapping-domain — 30 Port Adapter Mapping](#30-port-adapter-mapping-domain)
- [30-port-adapter-mapping-full — Port-to-Adapter Mapping Table Diagram](#30-port-adapter-mapping-full)
- [30-port-adapter-mapping-infra — 30 Port Adapter Mapping](#30-port-adapter-mapping-infra)
- [30-port-adapter-mapping-overview — 30 Port Adapter Mapping](#30-port-adapter-mapping-overview)
- [31-pipeline-run-lifecycle-dataflow — 31 Pipeline Run Lifecycle](#31-pipeline-run-lifecycle-dataflow)
- [31-pipeline-run-lifecycle-domain — 31 Pipeline Run Lifecycle](#31-pipeline-run-lifecycle-domain)
- [31-pipeline-run-lifecycle-full — Pipeline Run Lifecycle — From Config to Completion](#31-pipeline-run-lifecycle-full)
- [31-pipeline-run-lifecycle-infra — 31 Pipeline Run Lifecycle](#31-pipeline-run-lifecycle-infra)
- [31-pipeline-run-lifecycle-overview — 31 Pipeline Run Lifecycle](#31-pipeline-run-lifecycle-overview)
- [32-single-record-journey-dataflow — 32 Single Record Journey](#32-single-record-journey-dataflow)
- [32-single-record-journey-domain — 32 Single Record Journey](#32-single-record-journey-domain)
- [32-single-record-journey-full — Record Processing Pipeline — Single Record Journey](#32-single-record-journey-full)
- [32-single-record-journey-infra — 32 Single Record Journey](#32-single-record-journey-infra)
- [32-single-record-journey-overview — 32 Single Record Journey](#32-single-record-journey-overview)
- [33-cli-run-interaction-dataflow — 33 Cli Run Interaction](#33-cli-run-interaction-dataflow)
- [33-cli-run-interaction-domain — 33 Cli Run Interaction](#33-cli-run-interaction-domain)
- [33-cli-run-interaction-full — CLI Run Command → PipelineRunner Full Interaction](#33-cli-run-interaction-full)
- [33-cli-run-interaction-infra — 33 Cli Run Interaction](#33-cli-run-interaction-infra)
- [33-cli-run-interaction-overview — 33 Cli Run Interaction](#33-cli-run-interaction-overview)
- [34-batch-processing-flow-dataflow — 34 Batch Processing Flow](#34-batch-processing-flow-dataflow)
- [34-batch-processing-flow-domain — 34 Batch Processing Flow](#34-batch-processing-flow-domain)
- [34-batch-processing-flow-full — Batch Processing Flow — Extract to Write](#34-batch-processing-flow-full)
- [34-batch-processing-flow-infra — 34 Batch Processing Flow](#34-batch-processing-flow-infra)
- [34-batch-processing-flow-overview — 34 Batch Processing Flow](#34-batch-processing-flow-overview)
- [35-bootstrap-sequence-dataflow — 35 Bootstrap Sequence](#35-bootstrap-sequence-dataflow)
- [35-bootstrap-sequence-domain — 35 Bootstrap Sequence](#35-bootstrap-sequence-domain)
- [35-bootstrap-sequence-full — Composition Layer Bootstrap Sequence](#35-bootstrap-sequence-full)
- [35-bootstrap-sequence-infra — 35 Bootstrap Sequence](#35-bootstrap-sequence-infra)
- [35-bootstrap-sequence-overview — 35 Bootstrap Sequence](#35-bootstrap-sequence-overview)
- [36-architecture-principles-mindmap-dataflow — 36 Architecture Principles Mindmap](#36-architecture-principles-mindmap-dataflow)
- [36-architecture-principles-mindmap-domain — 36 Architecture Principles Mindmap](#36-architecture-principles-mindmap-domain)
- [36-architecture-principles-mindmap-full — Architecture Principles Mind Map](#36-architecture-principles-mindmap-full)
- [36-architecture-principles-mindmap-infra — 36 Architecture Principles Mindmap](#36-architecture-principles-mindmap-infra)
- [36-architecture-principles-mindmap-overview — 36 Architecture Principles Mindmap](#36-architecture-principles-mindmap-overview)
- [39-medallion-invariants-dataflow — 39 Medallion Invariants](#39-medallion-invariants-dataflow)
- [39-medallion-invariants-domain — 39 Medallion Invariants](#39-medallion-invariants-domain)
- [39-medallion-invariants-full — Medallion Architecture Invariants (ARCH-007)](#39-medallion-invariants-full)
- [39-medallion-invariants-infra — 39 Medallion Invariants](#39-medallion-invariants-infra)
- [39-medallion-invariants-overview — 39 Medallion Invariants](#39-medallion-invariants-overview)
- [41-error-classification-tree-dataflow — 41 Error Classification Tree](#41-error-classification-tree-dataflow)
- [41-error-classification-tree-domain — 41 Error Classification Tree](#41-error-classification-tree-domain)
- [41-error-classification-tree-full — Error Classification Decision Tree — Full Logic](#41-error-classification-tree-full)
- [41-error-classification-tree-infra — 41 Error Classification Tree](#41-error-classification-tree-infra)
- [41-error-classification-tree-overview — 41 Error Classification Tree](#41-error-classification-tree-overview)
- [44-cross-provider-enrichment-dataflow — 44 Cross Provider Enrichment](#44-cross-provider-enrichment-dataflow)
- [44-cross-provider-enrichment-domain — 44 Cross Provider Enrichment](#44-cross-provider-enrichment-domain)
- [44-cross-provider-enrichment-full — Cross-Provider Data Enrichment Flow — Publication](#44-cross-provider-enrichment-full)
- [44-cross-provider-enrichment-infra — 44 Cross Provider Enrichment](#44-cross-provider-enrichment-infra)
- [44-cross-provider-enrichment-overview — 44 Cross Provider Enrichment](#44-cross-provider-enrichment-overview)
- [46-yaml-config-resolution-dataflow — 46 Yaml Config Resolution](#46-yaml-config-resolution-dataflow)
- [46-yaml-config-resolution-domain — 46 Yaml Config Resolution](#46-yaml-config-resolution-domain)
- [46-yaml-config-resolution-full — YAML Configuration Resolution Chain](#46-yaml-config-resolution-full)
- [46-yaml-config-resolution-infra — 46 Yaml Config Resolution](#46-yaml-config-resolution-infra)
- [46-yaml-config-resolution-overview — 46 Yaml Config Resolution](#46-yaml-config-resolution-overview)
- [48-composite-phase-lifecycle-dataflow — 48 Composite Phase Lifecycle](#48-composite-phase-lifecycle-dataflow)
- [48-composite-phase-lifecycle-domain — 48 Composite Phase Lifecycle](#48-composite-phase-lifecycle-domain)
- [48-composite-phase-lifecycle-full — Composite Pipeline Phase Lifecycle (FSM)](#48-composite-phase-lifecycle-full)
- [48-composite-phase-lifecycle-infra — 48 Composite Phase Lifecycle](#48-composite-phase-lifecycle-infra)
- [48-composite-phase-lifecycle-overview — 48 Composite Phase Lifecycle](#48-composite-phase-lifecycle-overview)
- [50-exception-hierarchy-dataflow — 50 Exception Hierarchy](#50-exception-hierarchy-dataflow)
- [50-exception-hierarchy-domain — 50 Exception Hierarchy](#50-exception-hierarchy-domain)
- [50-exception-hierarchy-full — Exception Hierarchy — Full Tree](#50-exception-hierarchy-full)
- [50-exception-hierarchy-infra — 50 Exception Hierarchy](#50-exception-hierarchy-infra)
- [50-exception-hierarchy-overview — 50 Exception Hierarchy](#50-exception-hierarchy-overview)

\newpage

<div style="page-break-before: always;"></div>

## 00-legend — 00 Legend

![00-legend](views/png/00-legend.png)

### Описание
Диаграмма «00 Legend» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Legend. Родительская диаграмма: `(root)`. На схеме отражено примерно 44 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: 📋 Legend, Link Types. Показательные узлы для быстрого чтения: Main data flow: solid, 4px, Dependency/DI: dashed, 2px, Observability: gray, 1px, Error/Quarantine: red dashed, 2px, Codes used in diagrams, K01 = Transform & normalize.

### Метаданные
- Тип: `flowchart`
- Представление: `Legend`

\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component-dataflow — 01 Full System Component

![01-full-system-component-dataflow](views/png/01-full-system-component-dataflow.png)

### Описание
Диаграмма «01 Full System Component» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `01-full-system-component-full.mermaid`. На схеме отражено примерно 12 узлов и 8 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, PipelineRunner, BatchTransformer, PipelineExecutor, RecordProcessor, ActivityTransformer.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component-domain — 01 Full System Component

![01-full-system-component-domain](views/png/01-full-system-component-domain.png)

### Описание
Диаграмма «01 Full System Component» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `01-full-system-component-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer. Показательные узлы для быстрого чтения: DataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort, MetricsPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component-full — Full System Component Diagram

![01-full-system-component-full](views/png/01-full-system-component-full.png)

### Описание
Диаграмма «Full System Component Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Five-Layer Architecture), §1.2 (Ports & Adapters). На схеме отражено примерно 64 узлов и 78 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External Systems, Bioactivity Sources, Publication Sources, Interfaces Layer, Composition Layer, Application Layer. Показательные узлы для быстрого чтения: ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API, OpenAlex API. Связанный ADR: ADR-040.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-27`
- Представление: `Full`
- ADR: `ADR-040`

\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component-infra — 01 Full System Component

![01-full-system-component-infra](views/png/01-full-system-component-infra.png)

### Описание
Диаграмма «01 Full System Component» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `01-full-system-component-full.mermaid`. На схеме отражено примерно 20 узлов и 1 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: StoragePort, LockPort, CheckpointPort, QuarantinePort, MetricsPort, TracingPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 01-full-system-component-overview — 01 Full System Component

![01-full-system-component-overview](views/png/01-full-system-component-overview.png)

### Описание
Диаграмма «01 Full System Component» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `01-full-system-component-full.mermaid`. На схеме отражено примерно 12 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External Systems, Interfaces, Composition, Application, Domain Ports, Infrastructure. Показательные узлы для быстрого чтения: Provider APIs, CLI, Bootstrap, Factories, PipelineRunner, PipelineExecutor.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-dataflow — 01 High Level

![01-high-level-dataflow](views/png/01-high-level-dataflow.png)

### Описание
Диаграмма «01 High Level» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `01-high-level-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: Executor, Runner, Bronze, Silver, Gold, Sources.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-domain — 01 High Level

![01-high-level-domain](views/png/01-high-level-domain.png)

### Описание
Диаграмма «01 High Level» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `01-high-level-full.mermaid`. На схеме отражено примерно 20 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Boot, Trans, Sources, Runner, Executor, Adapters.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-full — High-Level System Architecture

![01-high-level-full](views/png/01-high-level-full.png)

### Описание
Диаграмма «High-Level System Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Five-Layer Architecture). На схеме отражено примерно 19 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External Data Sources, Interfaces Layer, Composition Layer, Application Layer, Infrastructure Layer, Data Lake — Local Storage. Показательные узлы для быстрого чтения: ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API, OpenAlex API.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-infra — 01 High Level

![01-high-level-infra](views/png/01-high-level-infra.png)

### Описание
Диаграмма «01 High Level» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `01-high-level-full.mermaid`. На схеме отражено примерно 20 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Executor, Runner, Storage, Adapters, Quarantine, Boot.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 01-high-level-overview — 01 High Level

![01-high-level-overview](views/png/01-high-level-overview.png)

### Описание
Диаграмма «01 High Level» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `01-high-level-full.mermaid`. На схеме отражено примерно 15 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Executor, Runner, Trans, Boot, Sources, Adapters.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 02-medallion-dataflow — 02 Medallion

![02-medallion-dataflow](views/png/02-medallion-dataflow.png)

### Описание
Диаграмма «02 Medallion» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `02-medallion-full.mermaid`. На схеме отражено примерно 12 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Bronze, Silver, normalize, flatten, B1, B2.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 02-medallion-domain — 02 Medallion

![02-medallion-domain](views/png/02-medallion-domain.png)

### Описание
Диаграмма «02 Medallion» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `02-medallion-full.mermaid`. На схеме отражено примерно 20 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: normalize, flatten, B1, B2, B3, B4.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 02-medallion-full — Medallion Architecture Layers

![02-medallion-full](views/png/02-medallion-full.png)

### Описание
Диаграмма «Medallion Architecture Layers» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Bronze/Silver/Gold), §2.3 (Quarantine). На схеме отражено примерно 15 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Bronze Layer, Silver Layer, Gold Layer, Quarantine. Показательные узлы для быстрого чтения: Raw Data JSONL + zstd, Append-Only writes, Retention: 90 days, content_hash tracking, Normalized Data Delta Lake (ACID), Merge by content_hash.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 02-medallion-infra — 02 Medallion

![02-medallion-infra](views/png/02-medallion-infra.png)

### Описание
Диаграмма «02 Medallion» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `02-medallion-full.mermaid`. На схеме отражено примерно 20 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Quarantine, Bronze, normalize, Silver, flatten, B1.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 02-medallion-overview — 02 Medallion

![02-medallion-overview](views/png/02-medallion-overview.png)

### Описание
Диаграмма «02 Medallion» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `02-medallion-full.mermaid`. На схеме отражено примерно 15 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: normalize, flatten, B1, B2, B3, B4.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 03-medallion-data-flow-full — 03 Medallion Data Flow

![03-medallion-data-flow-full](views/png/03-medallion-data-flow-full.png)

### Описание
Диаграмма «03 Medallion Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Full. Родительская диаграмма: `03-medallion-data-flow.mmd`. На схеме отражено примерно 8 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: External APIs, Ingestion rate-limit + retry, Bronze JSONL + metadata, Transform normalize + identity, Silver Delta + validator, Gold Delta + business schema.

### Метаданные
- Тип: `flowchart`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 03-medallion-data-flow-overview — 03 Medallion Data Flow

![03-medallion-data-flow-overview](views/png/03-medallion-data-flow-overview.png)

### Описание
Диаграмма «03 Medallion Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `03-medallion-data-flow.mmd`. На схеме отражено примерно 4 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Bronze, Silver, Gold, DQ + Quarantine.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram-dataflow — 04 Domain Layer Class Diagram

![04-domain-layer-class-diagram-dataflow](views/png/04-domain-layer-class-diagram-dataflow.png)

### Описание
Диаграмма «04 Domain Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`. На схеме отражено примерно 12 узлов и 8 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: PipelineConfig, DataSourcePort, FilterableDataSourcePort, QuarantinePort, TableConfig, DQConfig.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram-domain — 04 Domain Layer Class Diagram

![04-domain-layer-class-diagram-domain](views/png/04-domain-layer-class-diagram-domain.png)

### Описание
Диаграмма «04 Domain Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BaseEntity, TableConfig, PublicationEntityBase, PipelineConfig, DataSourcePort, FilterableDataSourcePort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram-full — Domain Layer Class Diagram

![04-domain-layer-class-diagram-full](views/png/04-domain-layer-class-diagram-full.png)

### Описание
Диаграмма «Domain Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Domain Layer), §1.2 (Ports), §1.3 (Entities).

### Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram-infra — 04 Domain Layer Class Diagram

![04-domain-layer-class-diagram-infra](views/png/04-domain-layer-class-diagram-infra.png)

### Описание
Диаграмма «04 Domain Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: StoragePort, LockPort, CheckpointPort, QuarantinePort, MetricsPort, TracingPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 04-domain-layer-class-diagram-overview — 04 Domain Layer Class Diagram

![04-domain-layer-class-diagram-overview](views/png/04-domain-layer-class-diagram-overview.png)

### Описание
Диаграмма «04 Domain Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`. На схеме отражено примерно 15 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: BaseEntity, PublicationEntityBase, PipelineConfig, TableConfig, DQConfig, FilterableDataSourcePort.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction-dataflow — 05 Layers Interaction

![05-layers-interaction-dataflow](views/png/05-layers-interaction-dataflow.png)

### Описание
Диаграмма «05 Layers Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `05-layers-interaction-full.mermaid`. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Ports, Runner, BatchExec, Transformer, Merger, CompositeRunner.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction-domain — 05 Layers Interaction

![05-layers-interaction-domain](views/png/05-layers-interaction-domain.png)

### Описание
Диаграмма «05 Layers Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `05-layers-interaction-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Ports, Exceptions, Domain, Factories, Coordinator, Application.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction-full — Layer Interaction — Hexagonal Architecture

![05-layers-interaction-full](views/png/05-layers-interaction-full.png)

### Описание
Диаграмма «Layer Interaction — Hexagonal Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Layers), §1.2 (Ports & Adapters). На схеме отражено примерно 19 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Interfaces Layer, Composition Layer, Application Layer, Composite Pipeline (ADR-026), Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CLI Entry Point, bootstrap_pipeline, PipelineRegistry, Factories, PipelineRunner, BatchExecutor.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction-infra — 05 Layers Interaction

![05-layers-interaction-infra](views/png/05-layers-interaction-infra.png)

### Описание
Диаграмма «05 Layers Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `05-layers-interaction-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Ports, Types, Exceptions, Runner, BatchExec, Transformer.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 05-layers-interaction-overview — 05 Layers Interaction

![05-layers-interaction-overview](views/png/05-layers-interaction-overview.png)

### Описание
Диаграмма «05 Layers Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `05-layers-interaction-full.mermaid`. На схеме отражено примерно 15 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Composition Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Ports, Types, Factories, Runner, BatchExec, Services.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states-dataflow — 05 Pipeline Lifecycle States

![05-pipeline-lifecycle-states-dataflow](views/png/05-pipeline-lifecycle-states-dataflow.png)

### Описание
Диаграмма «05 Pipeline Lifecycle States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`. На схеме отражено примерно 12 узлов и 8 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: ValidateLock, TRANSFORMING, FetchBatch, FailBatch, EXTRACTING, WriteBronze.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states-domain — 05 Pipeline Lifecycle States

![05-pipeline-lifecycle-states-domain](views/png/05-pipeline-lifecycle-states-domain.png)

### Описание
Диаграмма «05 Pipeline Lifecycle States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: ERROR, LoadingConfig, HealthChecks, PassRecords, WarnRecords, LogError.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states-full — Pipeline Lifecycle State Machine

![05-pipeline-lifecycle-states-full](views/png/05-pipeline-lifecycle-states-full.png)

### Описание
Диаграмма «Pipeline Lifecycle State Machine» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Pipeline Execution), §3.5 (Graceful Shutdown).

### Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states-infra — 05 Pipeline Lifecycle States

![05-pipeline-lifecycle-states-infra](views/png/05-pipeline-lifecycle-states-infra.png)

### Описание
Диаграмма «05 Pipeline Lifecycle States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`. На схеме отражено примерно 20 узлов и 23 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: ERROR, ValidateLock, VALIDATING, PREFLIGHT, TRANSFORMING, LOCK_ACQUIRING.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 05-pipeline-lifecycle-states-overview — 05 Pipeline Lifecycle States

![05-pipeline-lifecycle-states-overview](views/png/05-pipeline-lifecycle-states-overview.png)

### Описание
Диаграмма «05 Pipeline Lifecycle States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`. На схеме отражено примерно 15 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: LoadingConfig, ValidateLock, LogError, *, FetchBatch, FAILED.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram-dataflow — 06 Application Layer Class Diagram

![06-application-layer-class-diagram-dataflow](views/png/06-application-layer-class-diagram-dataflow.png)

### Описание
Диаграмма «06 Application Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: BaseChemblTransformer, RecordProcessor, BasePipeline, PipelineRunner, PipelineExecutor, BatchTransformer.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram-domain — 06 Application Layer Class Diagram

![06-application-layer-class-diagram-domain](views/png/06-application-layer-class-diagram-domain.png)

### Описание
Диаграмма «06 Application Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: RunnerServices, BaseChemblTransformer, RecordProcessor, BasePipeline, PipelineRunner, PipelineExecutor.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram-full — Application Layer Class Diagram

![06-application-layer-class-diagram-full](views/png/06-application-layer-class-diagram-full.png)

### Описание
Диаграмма «Application Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Application Layer), §3 (Pipeline Execution).

### Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram-infra — 06 Application Layer Class Diagram

![06-application-layer-class-diagram-infra](views/png/06-application-layer-class-diagram-infra.png)

### Описание
Диаграмма «06 Application Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: RunnerServices, RecordProcessor, PipelineRunner, BasePipeline, PipelineExecutor, BatchTransformer.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 06-application-layer-class-diagram-overview — 06 Application Layer Class Diagram

![06-application-layer-class-diagram-overview](views/png/06-application-layer-class-diagram-overview.png)

### Описание
Диаграмма «06 Application Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`. На схеме отражено примерно 15 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: PipelineRunner, RunnerServices, BaseChemblTransformer, BaseTransformer, PreflightService, PostrunService.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states-dataflow — 07 Circuit Breaker States

![07-circuit-breaker-states-dataflow](views/png/07-circuit-breaker-states-dataflow.png)

### Описание
Диаграмма «07 Circuit Breaker States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`. На схеме отражено примерно 12 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: RecordSuccess, RecordFailure, Success, ProcessRequest, *, CLOSED.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states-domain — 07 Circuit Breaker States

![07-circuit-breaker-states-domain](views/png/07-circuit-breaker-states-domain.png)

### Описание
Диаграмма «07 Circuit Breaker States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`. На схеме отражено примерно 20 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: RecordSuccess, RecordFailure, Success, ProcessRequest, *, CLOSED.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states-full — Circuit Breaker State Machine

![07-circuit-breaker-states-full](views/png/07-circuit-breaker-states-full.png)

### Описание
Диаграмма «Circuit Breaker State Machine» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), ADR-007.

### Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states-infra — 07 Circuit Breaker States

![07-circuit-breaker-states-infra](views/png/07-circuit-breaker-states-infra.png)

### Описание
Диаграмма «07 Circuit Breaker States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`. На схеме отражено примерно 20 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: HP, Blocking, *, CLOSED, ProcessRequest, OPEN.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 07-circuit-breaker-states-overview — 07 Circuit Breaker States

![07-circuit-breaker-states-overview](views/png/07-circuit-breaker-states-overview.png)

### Описание
Диаграмма «07 Circuit Breaker States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`. На схеме отражено примерно 15 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: *, CLOSED, ProcessRequest, SendProbe, Waiting, Operational.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow-dataflow — 08 Complete Etl Workflow

![08-complete-etl-workflow-dataflow](views/png/08-complete-etl-workflow-dataflow.png)

### Описание
Диаграмма «08 Complete Etl Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: A6, A7, A8, B1, A4, A5.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow-domain — 08 Complete Etl Workflow

![08-complete-etl-workflow-domain](views/png/08-complete-etl-workflow-domain.png)

### Описание
Диаграмма «08 Complete Etl Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: B1, B2, B4, B3, B5, B8.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow-full — Complete ETL Workflow (6 Phases)

![08-complete-etl-workflow-full](views/png/08-complete-etl-workflow-full.png)

### Описание
Диаграмма «Complete ETL Workflow (6 Phases)» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Pipeline Execution), §3.2 (Preflight), §3.4 (Postrun). На схеме отражено примерно 16 узлов и 57 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Phase 1: Prepare, Phase 2: Extract, Phase 3: Transform, Normalization Rules, Metadata Fields, Phase 4: Validate. Показательные узлы для быстрого чтения: Load YAML Config, Fetch from API, Load Bronze Records, NaN/Inf → null, Floats → round(10), Dates → ISO YYYY-MM-DD.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow-infra — 08 Complete Etl Workflow

![08-complete-etl-workflow-infra](views/png/08-complete-etl-workflow-infra.png)

### Описание
Диаграмма «08 Complete Etl Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: A6, A7, A8, B1, A4, A5.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 08-complete-etl-workflow-overview — 08 Complete Etl Workflow

![08-complete-etl-workflow-overview](views/png/08-complete-etl-workflow-overview.png)

### Описание
Диаграмма «08 Complete Etl Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`. На схеме отражено примерно 15 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: D8, D7, D10, E_ERR, D9, E1.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd-dataflow — 08 Domain Ddd

![08-domain-ddd-dataflow](views/png/08-domain-ddd-dataflow.png)

### Описание
Диаграмма «08 Domain Ddd» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `08-domain-ddd-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: BatchID, RunID, EntityID, Batch, PipelineRun, BatchCreated.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd-domain — 08 Domain Ddd

![08-domain-ddd-domain](views/png/08-domain-ddd-domain.png)

### Описание
Диаграмма «08 Domain Ddd» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `08-domain-ddd-full.mermaid`. На схеме отражено примерно 20 узлов и 15 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: BatchID, EntityID, ContentHash, HealthStatus, RunID, RunStarted.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd-full — Domain Layer — DDD Components

![08-domain-ddd-full](views/png/08-domain-ddd-full.png)

### Описание
Диаграмма «Domain Layer — DDD Components» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Domain Layer), §1.3 (DDD Aggregates), ADR-021. На схеме отражено примерно 12 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer (DDD), ports/, aggregates/, Domain Events, value_objects/, types.py. Показательные узлы для быстрого чтения: Batch Aggregate add_record(), quarantine_record() seal(), mark_committed(), PipelineRun Aggregate start(), record_stage_success() complete(), fail(), QuarantineEntry Aggregate mark_retrying(), mark_recovered() mark_dead_letter(), RunID (UUID), BatchID (UUID), EntityID (str).

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd-infra — 08 Domain Ddd

![08-domain-ddd-infra](views/png/08-domain-ddd-infra.png)

### Описание
Диаграмма «08 Domain Ddd» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `08-domain-ddd-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: RunID, BatchID, EntityID, Batch, PipelineRun, BatchCreated.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 08-domain-ddd-overview — 08 Domain Ddd

![08-domain-ddd-overview](views/png/08-domain-ddd-overview.png)

### Описание
Диаграмма «08 Domain Ddd» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `08-domain-ddd-full.mermaid`. На схеме отражено примерно 15 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: RunID, BatchID, Batch, BatchCreated, BatchSealed, BatchWritten.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram-dataflow — 10 Infrastructure Layer Class Diagram

![10-infrastructure-layer-class-diagram-dataflow](views/png/10-infrastructure-layer-class-diagram-dataflow.png)

### Описание
Диаграмма «10 Infrastructure Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: DataSourcePort, FilterableDataSourcePort, QuarantinePort, StoragePort, SilverWriter, GoldWriter.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram-domain — 10 Infrastructure Layer Class Diagram

![10-infrastructure-layer-class-diagram-domain](views/png/10-infrastructure-layer-class-diagram-domain.png)

### Описание
Диаграмма «10 Infrastructure Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: DataSourcePort, StoragePort, CsvExporter, MetricsPort, RetryPolicy, FilterableDataSourcePort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram-full — Infrastructure Layer Class Diagram

![10-infrastructure-layer-class-diagram-full](views/png/10-infrastructure-layer-class-diagram-full.png)

### Описание
Диаграмма «Infrastructure Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Infrastructure Layer), §3.6 (Resilience).

### Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram-infra — 10 Infrastructure Layer Class Diagram

![10-infrastructure-layer-class-diagram-infra](views/png/10-infrastructure-layer-class-diagram-infra.png)

### Описание
Диаграмма «10 Infrastructure Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`. На схеме отражено примерно 20 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: StoragePort, MetricsPort, LockPort, CheckpointPort, QuarantinePort, LoggerPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 10-infrastructure-layer-class-diagram-overview — 10 Infrastructure Layer Class Diagram

![10-infrastructure-layer-class-diagram-overview](views/png/10-infrastructure-layer-class-diagram-overview.png)

### Описание
Диаграмма «10 Infrastructure Layer Class Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`. На схеме отражено примерно 15 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: RetryPolicy, DataSourcePort, StoragePort, FilterableDataSourcePort, CsvExporter, ChemblAdapter.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture-dataflow — 12 Local Deployment Architecture

![12-local-deployment-architecture-dataflow](views/png/12-local-deployment-architecture-dataflow.png)

### Описание
Диаграмма «12 Local Deployment Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Bronze, Silver, Gold, chembl_activity, pubchem_compound, uniprot_protein.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture-domain — 12 Local Deployment Architecture

![12-local-deployment-architecture-domain](views/png/12-local-deployment-architecture-domain.png)

### Описание
Диаграмма «12 Local Deployment Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`. На схеме отражено примерно 20 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: chembl_activity, pubchem_compound, uniprot_protein, ChEMBL_API, PubChem_API, UniProt_API.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture-full — Local Deployment Architecture

![12-local-deployment-architecture-full](views/png/12-local-deployment-architecture-full.png)

### Описание
Диаграмма «Local Deployment Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §5.6 (Deployment), ADR-010 (Local-Only). На схеме отражено примерно 21 узлов и 23 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External APIs, Local Machine (Single Instance), CLI Execution, Local Pipeline Workers, In-Process Locking, Local filesystem (data/). Показательные узлы для быстрого чтения: 🌐 ChEMBL API ebi.ac.uk/chembl, 🌐 PubChem API pubchem.ncbi.nlm.nih.gov, 🌐 UniProt API uniprot.org, 🌐 PubMed API eutils.ncbi.nlm.nih.gov, 🖥️ CLI / Manual run PipelineRunner, ⏰ Local scheduler (cron/systemd).

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture-infra — 12 Local Deployment Architecture

![12-local-deployment-architecture-infra](views/png/12-local-deployment-architecture-infra.png)

### Описание
Диаграмма «12 Local Deployment Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`. На схеме отражено примерно 20 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Quarantine, Checkpoints, Metrics, MemoryLock, chembl_activity, pubchem_compound.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 12-local-deployment-architecture-overview — 12 Local Deployment Architecture

![12-local-deployment-architecture-overview](views/png/12-local-deployment-architecture-overview.png)

### Описание
Диаграмма «12 Local Deployment Architecture» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`. На схеме отражено примерно 15 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: chembl_activity, ChEMBL_API, PubMed_API, Lineage, Logs, pubchem_compound.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 13-port-protocol-contracts-full — 13 Port Protocol Contracts

![13-port-protocol-contracts-full](views/png/13-port-protocol-contracts-full.png)

### Описание
Диаграмма «13 Port Protocol Contracts» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Full. Родительская диаграмма: `13-port-protocol-contracts.mmd`. На схеме отражено примерно 9 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Port Groups, Implementations. Показательные узлы для быстрого чтения: Data Source Ports, Storage + Validation Ports, Observability Ports, Operational Ports, Provider Adapters, Writers + Readers.

### Метаданные
- Тип: `flowchart`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 13-port-protocol-contracts-overview — 13 Port Protocol Contracts

![13-port-protocol-contracts-overview](views/png/13-port-protocol-contracts-overview.png)

### Описание
Диаграмма «13 Port Protocol Contracts» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `13-port-protocol-contracts.mmd`. На схеме отражено примерно 3 узлов и 3 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Domain Port Catalog, Implementation Catalog, Import Matrix / Contracts.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states-dataflow — 14 Provider Health States

![14-provider-health-states-dataflow](views/png/14-provider-health-states-dataflow.png)

### Описание
Диаграмма «14 Provider Health States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `14-provider-health-states-full.mermaid`. На схеме отражено примерно 12 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: WatchingErrors, ErrorAccumulating, *, ProcessingRequest, HEALTHY, DEGRADED.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states-domain — 14 Provider Health States

![14-provider-health-states-domain](views/png/14-provider-health-states-domain.png)

### Описание
Диаграмма «14 Provider Health States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `14-provider-health-states-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Composition Layer. Показательные узлы для быстрого чтения: WatchingErrors, HEALTHY, ErrorAccumulating, UNHEALTHY, MinorError, *.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states-full — Provider Health State Machine

![14-provider-health-states-full](views/png/14-provider-health-states-full.png)

### Описание
Диаграмма «Provider Health State Machine» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.6 (Resilience), §4 (Provider Specifications).

### Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states-infra — 14 Provider Health States

![14-provider-health-states-infra](views/png/14-provider-health-states-infra.png)

### Описание
Диаграмма «14 Provider Health States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `14-provider-health-states-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: HP, WatchingErrors, ErrorAccumulating, MinorError, *, ProcessingRequest.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 14-provider-health-states-overview — 14 Provider Health States

![14-provider-health-states-overview](views/png/14-provider-health-states-overview.png)

### Описание
Диаграмма «14 Provider Health States» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `14-provider-health-states-full.mermaid`. На схеме отражено примерно 15 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Composition Layer. Показательные узлы для быстрого чтения: WatchingErrors, ErrorAccumulating, MinorError, *, ProcessingRequest, HEALTHY.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow-dataflow — 15 Dq Check Workflow

![15-dq-check-workflow-dataflow](views/png/15-dq-check-workflow-dataflow.png)

### Описание
Диаграмма «15 Dq Check Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`. На схеме отражено примерно 12 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: record_error_rate, Schema Validation, Required Fields, Error Rate, Type Checks, Value Rules.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow-domain — 15 Dq Check Workflow

![15-dq-check-workflow-domain](views/png/15-dq-check-workflow-domain.png)

### Описание
Диаграмма «15 Dq Check Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Schema Validation, Required Fields, Error Rate, Type Checks, Value Rules, Relation Checks.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow-full — Data Quality Check Workflow

![15-dq-check-workflow-full](views/png/15-dq-check-workflow-full.png)

### Описание
Диаграмма «Data Quality Check Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.1 (DQ Checks), §2.3 (Quarantine). На схеме отражено примерно 25 узлов и 29 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Input Stage, Validation Stage, Error Classification, Action Paths, Record Routing, Metrics Export. Показательные узлы для быстрого чтения: /"📥 Input Records (from Bronze)"/, 🔍 Pandera Schema Validation, Check required fields, Validate data types, Check value constraints, Validate relationships.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow-infra — 15 Dq Check Workflow

![15-dq-check-workflow-infra](views/png/15-dq-check-workflow-infra.png)

### Описание
Диаграмма «15 Dq Check Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: record_error_rate, Schema Validation, Required Fields, Error Rate, Type Checks, Value Rules.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 15-dq-check-workflow-overview — 15 Dq Check Workflow

![15-dq-check-workflow-overview](views/png/15-dq-check-workflow-overview.png)

### Описание
Диаграмма «15 Dq Check Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`. На схеме отражено примерно 15 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer. Показательные узлы для быстрого чтения: record_error_rate, Schema Validation, Required Fields, Type Checks, Value Rules, Relation Checks.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 16-transformer-hierarchy-full — 16 Transformer Hierarchy

![16-transformer-hierarchy-full](views/png/16-transformer-hierarchy-full.png)

### Описание
Диаграмма «16 Transformer Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Full. Родительская диаграмма: `16-transformer-hierarchy.mmd`. На схеме отражено примерно 6 узлов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: BaseTransformer, ChEMBL Transformers, Publication Transformers, UniProt Transformers, Other Transformers, Extractor Pattern.

### Метаданные
- Тип: `flowchart`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 16-transformer-hierarchy-overview — 16 Transformer Hierarchy

![16-transformer-hierarchy-overview](views/png/16-transformer-hierarchy-overview.png)

### Описание
Диаграмма «16 Transformer Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `16-transformer-hierarchy.mmd`. На схеме отражено примерно 3 узлов и 2 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Template Method, Transformer Families, Reusable Extractors.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow-dataflow — 21 Activity Entity Data Flow

![21-activity-entity-data-flow-dataflow](views/png/21-activity-entity-data-flow-dataflow.png)

### Описание
Диаграмма «21 Activity Entity Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Fetch Activity Batch, Fetch Related IDs, Write Bronze, Record Lineage, Normalize Units, Add Metadata.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow-domain — 21 Activity Entity Data Flow

![21-activity-entity-data-flow-domain](views/png/21-activity-entity-data-flow-domain.png)

### Описание
Диаграмма «21 Activity Entity Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`. На схеме отражено примерно 20 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Fetch Activity Batch, Fetch Related IDs, Write Bronze, Record Lineage, Normalize Units, Add Metadata.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow-full — Activity Entity Data Flow (Extract → Transform → Load)

![21-activity-entity-data-flow-full](views/png/21-activity-entity-data-flow-full.png)

### Описание
Диаграмма «Activity Entity Data Flow (Extract → Transform → Load)» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.8 (Transformation), §4.1 (ChEMBL Activity). На схеме отражено примерно 30 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: External API, Extract Phase, Transform Phase, Validate Phase, Load Phase, Related Entities (Silver). Показательные узлы для быстрого чтения: 🌐 ChEMBL API /activities endpoint, 📥 Fetch activity_id batch (ChemblAdapter), 🔗 Fetch related entities assay_id, molecule_id, target_id, 💾 Write Bronze JSONL + zstd, 📊 Record Lineage batch_id, paths, 🔧 Normalize units nM → μM standardization.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow-infra — 21 Activity Entity Data Flow

![21-activity-entity-data-flow-infra](views/png/21-activity-entity-data-flow-infra.png)

### Описание
Диаграмма «21 Activity Entity Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`. На схеме отражено примерно 20 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Local FS, Fetch Activity Batch, Fetch Related IDs, Write Bronze, Record Lineage, Normalize Units.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 21-activity-entity-data-flow-overview — 21 Activity Entity Data Flow

![21-activity-entity-data-flow-overview](views/png/21-activity-entity-data-flow-overview.png)

### Описание
Диаграмма «21 Activity Entity Data Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`. На схеме отражено примерно 15 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Fetch Activity Batch, Fetch Related IDs, Write Bronze, Record Lineage, Normalize Units, Add Metadata.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters-dataflow — 26 Hexagonal Ports Adapters

![26-hexagonal-ports-adapters-dataflow](views/png/26-hexagonal-ports-adapters-dataflow.png)

### Описание
Диаграмма «26 Hexagonal Ports Adapters» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, StoragePort, ChemblAdapter, PubchemAdapter, UniprotAdapter, PubmedAdapter.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters-domain — 26 Hexagonal Ports Adapters

![26-hexagonal-ports-adapters-domain](views/png/26-hexagonal-ports-adapters-domain.png)

### Описание
Диаграмма «26 Hexagonal Ports Adapters» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`. На схеме отражено примерно 20 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DQMonitorPort, DataSourcePort, StoragePort, DeltaReaderPort, LockPort, CheckpointPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters-full — Hexagonal Architecture — Ports and Adapters Overview

![26-hexagonal-ports-adapters-full](views/png/26-hexagonal-ports-adapters-full.png)

### Описание
Диаграмма «Hexagonal Architecture — Ports and Adapters Overview» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.2 (Ports & Adapters), §1.1 (Five-Layer Architecture). На схеме отражено примерно 48 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer — Ports (Protocol), Data Ports, Coordination Ports, Observability Ports, Quality & Security Ports, Metadata & Config Ports. Показательные узлы для быстрого чтения: DataSourcePort • fetch() → AsyncIterator • health_check() → HealthStatus, FilterableDataSourcePort • fetch_filtered(), StoragePort • write_bronze() • write_silver() • write_gold(), DeltaReaderPort • read_table() • get_schema(), LockPort • acquire() • release() • renew(), CheckpointPort • save() • load() • delete().

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters-infra — 26 Hexagonal Ports Adapters

![26-hexagonal-ports-adapters-infra](views/png/26-hexagonal-ports-adapters-infra.png)

### Описание
Диаграмма «26 Hexagonal Ports Adapters» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`. На схеме отражено примерно 20 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, StoragePort, DeltaReaderPort, LockPort, CheckpointPort, QuarantinePort.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 26-hexagonal-ports-adapters-overview — 26 Hexagonal Ports Adapters

![26-hexagonal-ports-adapters-overview](views/png/26-hexagonal-ports-adapters-overview.png)

### Описание
Диаграмма «26 Hexagonal Ports Adapters» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`. На схеме отражено примерно 15 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DataSourcePort, StoragePort, DeltaReaderPort, LockPort, ChemblAdapter, PubchemAdapter.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph-dataflow — 28 Composition Root Di Graph

![28-composition-root-di-graph-dataflow](views/png/28-composition-root-di-graph-dataflow.png)

### Описание
Диаграмма «28 Composition Root Di Graph» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`. На схеме отражено примерно 12 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: BOOT, SB, BL, HCF, DSF, STF.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph-domain — 28 Composition Root Di Graph

![28-composition-root-di-graph-domain](views/png/28-composition-root-di-graph-domain.png)

### Описание
Диаграмма «28 Composition Root Di Graph» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`. На схеме отражено примерно 20 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: DQF, BOOT, SB, BL, HCF, DSF.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph-full — Composition Root Wiring — Full DI Graph

![28-composition-root-di-graph-full](views/png/28-composition-root-di-graph-full.png)

### Описание
Диаграмма «Composition Root Wiring — Full DI Graph» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Composition Layer), ADR-005. На схеме отражено примерно 19 узлов и 35 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Entry Point, Composition Factories, Logger & Observability, Client & Data Source, Storage & Services, Pipeline Construction. Показательные узлы для быстрого чтения: CLI run command, bootstrap/runtime/assembly.py, BootstrapLogger • configure structlog, DQServicesFactory • create() → DQ analyzers + monitor, HttpClientFactory • create(provider) → UnifiedHTTPClient, DataSourceFactory • create(provider, config) → DataSourcePort impl.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph-infra — 28 Composition Root Di Graph

![28-composition-root-di-graph-infra](views/png/28-composition-root-di-graph-infra.png)

### Описание
Диаграмма «28 Composition Root Di Graph» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`. На схеме отражено примерно 20 узлов и 19 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: ADP, BOOT, SB, BL, HCF, DSF.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 28-composition-root-di-graph-overview — 28 Composition Root Di Graph

![28-composition-root-di-graph-overview](views/png/28-composition-root-di-graph-overview.png)

### Описание
Диаграмма «28 Composition Root Di Graph» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`. На схеме отражено примерно 12 узлов и 15 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Entry, Composition Factories, Created Runtime. Показательные узлы для быстрого чтения: CLI run, Bootstrap runtime, LoggerFactory, HttpClientFactory, DataSourceFactory, StorageFactory.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow-dataflow — 29 Composite Pipeline Workflow

![29-composite-pipeline-workflow-dataflow](views/png/29-composite-pipeline-workflow-dataflow.png)

### Описание
Диаграмма «29 Composite Pipeline Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: SP, Merge, Gold, CCM, Deps, Enrich.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow-domain — 29 Composite Pipeline Workflow

![29-composite-pipeline-workflow-domain](views/png/29-composite-pipeline-workflow-domain.png)

### Описание
Диаграмма «29 Composite Pipeline Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: EC, KEYS, KE, SB, DC, SP.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow-full — Composite Pipeline Full Workflow — Seed to Gold (ADR-026)

![29-composite-pipeline-workflow-full](views/png/29-composite-pipeline-workflow-full.png)

### Описание
Диаграмма «Composite Pipeline Full Workflow — Seed to Gold (ADR-026)» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.10 (Composite Pipelines), ADR-026. На схеме отражено примерно 25 узлов и 40 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Phase 1: Initialization, Phase 2: Seed Pipeline, Phase 3: Dependencies, Phase 3.5: Key Extraction, Phase 4: Fan-Out Enrichment, Enricher Workers. Показательные узлы для быстрого чтения: [S] Load CompositeConfig from YAML, [S] bootstrap_composite_runner() → CompositePipelineRunner, [S] Run Seed Pipeline (e.g., chembl_publication), ("[D, [S] DependencyCoordinator • run_dependencies(), [S] Dependency 1 (e.g., uniprot_protein).

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow-infra — 29 Composite Pipeline Workflow

![29-composite-pipeline-workflow-infra](views/png/29-composite-pipeline-workflow-infra.png)

### Описание
Диаграмма «29 Composite Pipeline Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`. На схеме отражено примерно 20 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: SP, EC, KEYS, KE, SB, DC.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 29-composite-pipeline-workflow-overview — 29 Composite Pipeline Workflow

![29-composite-pipeline-workflow-overview](views/png/29-composite-pipeline-workflow-overview.png)

### Описание
Диаграмма «29 Composite Pipeline Workflow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`. На схеме отражено примерно 2 узлов и 15 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: [S] CompositeConfig, [S] CheckpointManager.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping-dataflow — 30 Port Adapter Mapping

![30-port-adapter-mapping-dataflow](views/png/30-port-adapter-mapping-dataflow.png)

### Описание
Диаграмма «30 Port Adapter Mapping» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`. На схеме отражено примерно 12 узлов и 6 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: P1, P2, P3, P4, P5, P6.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping-domain — 30 Port Adapter Mapping

![30-port-adapter-mapping-domain](views/png/30-port-adapter-mapping-domain.png)

### Описание
Диаграмма «30 Port Adapter Mapping» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: P1, P2, P3, P4, P5, P6.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping-full — Port-to-Adapter Mapping Table Diagram

![30-port-adapter-mapping-full](views/png/30-port-adapter-mapping-full.png)

### Описание
Диаграмма «Port-to-Adapter Mapping Table Diagram» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.2 (Ports & Adapters), ARCH-008 (Single Source). На схеме отражено примерно 54 узлов и 79 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Ports (domain/ports/), Core Data & State, Observability & DQ, Validation & Policy, Runtime Controls, Infrastructure Adapters. Показательные узлы для быстрого чтения: [P] DataSourcePort, [P] FilterableDataSourcePort, [P] StoragePort, [P] LockPort, [P] CheckpointPort, [P] QuarantinePort.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-27`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping-infra — 30 Port Adapter Mapping

![30-port-adapter-mapping-infra](views/png/30-port-adapter-mapping-infra.png)

### Описание
Диаграмма «30 Port Adapter Mapping» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`. На схеме отражено примерно 20 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: P1, P2, P3, P4, P5, P6.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 30-port-adapter-mapping-overview — 30 Port Adapter Mapping

![30-port-adapter-mapping-overview](views/png/30-port-adapter-mapping-overview.png)

### Описание
Диаграмма «30 Port Adapter Mapping» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`. На схеме отражено примерно 10 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Port Families, Infrastructure Adapter Families, Fallbacks. Показательные узлы для быстрого чтения: [P] Core Data Ports, [P] Observability Ports, [P] Validation/Policy Ports, [P] Runtime Control Ports, [A] Provider Adapters, [A] Storage Adapters.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle-dataflow — 31 Pipeline Run Lifecycle

![31-pipeline-run-lifecycle-dataflow](views/png/31-pipeline-run-lifecycle-dataflow.png)

### Описание
Диаграмма «31 Pipeline Run Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`. На схеме отражено примерно 12 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: VALIDATING, PREFLIGHT, TRANSFORMING, BATCH_DONE, BatchLoop, PREFLIGHT_PASSED.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle-domain — 31 Pipeline Run Lifecycle

![31-pipeline-run-lifecycle-domain](views/png/31-pipeline-run-lifecycle-domain.png)

### Описание
Диаграмма «31 Pipeline Run Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`. На схеме отражено примерно 20 узлов и 27 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: EXTRACTING, FAILED, WRITING, VALIDATING, DRAINING, RELEASING.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle-full — Pipeline Run Lifecycle — From Config to Completion

![31-pipeline-run-lifecycle-full](views/png/31-pipeline-run-lifecycle-full.png)

### Описание
Диаграмма «Pipeline Run Lifecycle — From Config to Completion» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3 (Execution), domain/aggregates/pipeline_run.py.

### Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle-infra — 31 Pipeline Run Lifecycle

![31-pipeline-run-lifecycle-infra](views/png/31-pipeline-run-lifecycle-infra.png)

### Описание
Диаграмма «31 Pipeline Run Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`. На схеме отражено примерно 20 узлов и 36 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: VALIDATING, PREFLIGHT, POSTRUN, PREFLIGHT_PASSED, TRANSFORMING, BATCH_DONE.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 31-pipeline-run-lifecycle-overview — 31 Pipeline Run Lifecycle

![31-pipeline-run-lifecycle-overview](views/png/31-pipeline-run-lifecycle-overview.png)

### Описание
Диаграмма «31 Pipeline Run Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`. На схеме отражено примерно 15 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: VALIDATING, EXTRACTING, FAILED, PREFLIGHT_PASSED, TRANSFORMING, DRAINING.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey-dataflow — 32 Single Record Journey

![32-single-record-journey-dataflow](views/png/32-single-record-journey-dataflow.png)

### Описание
Диаграмма «32 Single Record Journey» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `32-single-record-journey-full.mermaid`. На схеме отражено примерно 12 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: SW, ST, TFG, GV, GW, CLEAN.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey-domain — 32 Single Record Journey

![32-single-record-journey-domain](views/png/32-single-record-journey-domain.png)

### Описание
Диаграмма «32 Single Record Journey» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `32-single-record-journey-full.mermaid`. На схеме отражено примерно 20 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: HASH, DQ, META, NORM, TI, BT.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey-full — Record Processing Pipeline — Single Record Journey

![32-single-record-journey-full](views/png/32-single-record-journey-full.png)

### Описание
Диаграмма «Record Processing Pipeline — Single Record Journey» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1-§2.6 (Data Flow, DQ), §2.8 (Normalization). На схеме отражено примерно 18 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: 1. External API, 2. Bronze Layer, 3. Transform (RecordProcessor), 4. Validate, 5. Route Decision, 6. Silver Layer. Показательные узлы для быстрого чтения: REST API Response (e.g., ChEMBL /activity), BronzeWriter.write_bronze() JSONL + zstd + atomic rename manifest update, ("Bronze File bronze/chembl/activity/ 2026-02-17/batch_001.jsonl.zst"  ), BatchTransformer.transform(), BaseTransformer._transform_impl() (e.g., ActivityTransformer), Add Metadata _run_id, _run_type _source_batch_id, _ingestion_ts.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey-infra — 32 Single Record Journey

![32-single-record-journey-infra](views/png/32-single-record-journey-infra.png)

### Описание
Диаграмма «32 Single Record Journey» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `32-single-record-journey-full.mermaid`. На схеме отражено примерно 20 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: SW, ST, TFG, GV, GW, CLEAN.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 32-single-record-journey-overview — 32 Single Record Journey

![32-single-record-journey-overview](views/png/32-single-record-journey-overview.png)

### Описание
Диаграмма «32 Single Record Journey» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `32-single-record-journey-full.mermaid`. На схеме отражено примерно 15 узлов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: ST, BF, BT, TI, NORM, META.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction-dataflow — 33 Cli Run Interaction

![33-cli-run-interaction-dataflow](views/png/33-cli-run-interaction-dataflow.png)

### Описание
Диаграмма «33 Cli Run Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`. На схеме отражено примерно 12 узлов и 20 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Application Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: Runner, PRS, Boot, PF, LM, BE.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction-domain — 33 Cli Run Interaction

![33-cli-run-interaction-domain](views/png/33-cli-run-interaction-domain.png)

### Описание
Диаграмма «33 Cli Run Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`. На схеме отражено примерно 20 узлов и 28 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Interfaces Layer. Показательные узлы для быстрого чтения: config, health, errors, DQ, PRS, Boot.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction-full — CLI Run Command → PipelineRunner Full Interaction

![33-cli-run-interaction-full](views/png/33-cli-run-interaction-full.png)

### Описание
Диаграмма «CLI Run Command → PipelineRunner Full Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Interfaces → Composition → Application).

### Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction-infra — 33 Cli Run Interaction

![33-cli-run-interaction-infra](views/png/33-cli-run-interaction-infra.png)

### Описание
Диаграмма «33 Cli Run Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`. На схеме отражено примерно 20 узлов и 28 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Interfaces Layer. Показательные узлы для быстрого чтения: config, owner_id, Runner, storage, metrics, PF.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 33-cli-run-interaction-overview — 33 Cli Run Interaction

![33-cli-run-interaction-overview](views/png/33-cli-run-interaction-overview.png)

### Описание
Диаграмма «33 Cli Run Interaction» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`. На схеме отражено примерно 15 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Interfaces Layer. Показательные узлы для быстрого чтения: config, owner_id, PRS, Runner, PF, LM.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow-dataflow — 34 Batch Processing Flow

![34-batch-processing-flow-dataflow](views/png/34-batch-processing-flow-dataflow.png)

### Описание
Диаграмма «34 Batch Processing Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`. На схеме отражено примерно 12 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: errors, Runner, batch_num, Bronze, Silver, Gold.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow-domain — 34 Batch Processing Flow

![34-batch-processing-flow-domain](views/png/34-batch-processing-flow-domain.png)

### Описание
Диаграмма «34 Batch Processing Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`. На схеме отражено примерно 20 узлов и 25 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: errors, error_count, BatchExecutor, BatchTransformer, BatchTracingManager, DataSourcePort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow-full — Batch Processing Flow — Extract to Write

![34-batch-processing-flow-full](views/png/34-batch-processing-flow-full.png)

### Описание
Диаграмма «Batch Processing Flow — Extract to Write» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма последовательности (sequence) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Data Flow), application/core/batch_executor.py.

### Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow-infra — 34 Batch Processing Flow

![34-batch-processing-flow-infra](views/png/34-batch-processing-flow-infra.png)

### Описание
Диаграмма «34 Batch Processing Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`. На схеме отражено примерно 20 узлов и 25 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: strip_values, errors, filter_ids, _run_type, PipelineRunner, BatchExecutor.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 34-batch-processing-flow-overview — 34 Batch Processing Flow

![34-batch-processing-flow-overview](views/png/34-batch-processing-flow-overview.png)

### Описание
Диаграмма «34 Batch Processing Flow» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`. На схеме отражено примерно 15 узлов и 20 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: strip, errors, filter_ids, error_count, BE, BT.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence-dataflow — 35 Bootstrap Sequence

![35-bootstrap-sequence-dataflow](views/png/35-bootstrap-sequence-dataflow.png)

### Описание
Диаграмма «35 Bootstrap Sequence» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: S2A, S1B, S2B, S3A, S3B, S4A.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence-domain — 35 Bootstrap Sequence

![35-bootstrap-sequence-domain](views/png/35-bootstrap-sequence-domain.png)

### Описание
Диаграмма «35 Bootstrap Sequence» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: S2A, S1B, S2B, S3A, S3B, S4A.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence-full — Composition Layer Bootstrap Sequence

![35-bootstrap-sequence-full](views/png/35-bootstrap-sequence-full.png)

### Описание
Диаграмма «Composition Layer Bootstrap Sequence» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Composition Root), composition/bootstrap/runtime/. На схеме отражено примерно 35 узлов и 27 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Step 1: Logger, Step 2: Configuration, Step 3: Observability Bundle, Step 4: Storage, Step 5: HTTP Client, Step 6: Data Source. Показательные узлы для быстрого чтения: BootstrapLogger.configure(), StructlogLogger (JSON, ISO timestamps, run_id binding), ConfigLoader.load(pipeline_name), PipelineYamlConfig (_base.yaml merged with entity.yaml), DQConfigLoader.load(), FilterConfigLoader.load().

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence-infra — 35 Bootstrap Sequence

![35-bootstrap-sequence-infra](views/png/35-bootstrap-sequence-infra.png)

### Описание
Диаграмма «35 Bootstrap Sequence» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: S2A, S1B, S2B, S3A, S3B, S4A.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 35-bootstrap-sequence-overview — 35 Bootstrap Sequence

![35-bootstrap-sequence-overview](views/png/35-bootstrap-sequence-overview.png)

### Описание
Диаграмма «35 Bootstrap Sequence» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`. На схеме отражено примерно 15 узлов и 15 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: S5A, S5B, S1B, S2A, S2B, S4D.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap-dataflow — 36 Architecture Principles Mindmap

![36-architecture-principles-mindmap-dataflow](views/png/36-architecture-principles-mindmap-dataflow.png)

### Описание
Диаграмма «36 Architecture Principles Mindmap» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`. На схеме отражено примерно 12 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: DataSourcePort, Batch, PipelineRun, PipelineRunner, BatchExecutor, 23 Transformers.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap-domain — 36 Architecture Principles Mindmap

![36-architecture-principles-mindmap-domain](views/png/36-architecture-principles-mindmap-domain.png)

### Описание
Диаграмма «36 Architecture Principles Mindmap» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`. На схеме отражено примерно 20 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Composition Layer. Показательные узлы для быстрого чтения: 24 Domain Ports, Domain, DDD Aggregates, DataSourcePort, StoragePort, LockPort.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap-full — Architecture Principles Mind Map

![36-architecture-principles-mindmap-full](views/png/36-architecture-principles-mindmap-full.png)

### Описание
Диаграмма «Architecture Principles Mind Map» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате интеллект-карта (mindmap) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1 (Architecture), all ADRs.

### Метаданные
- Тип: `mindmap`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap-infra — 36 Architecture Principles Mindmap

![36-architecture-principles-mindmap-infra](views/png/36-architecture-principles-mindmap-infra.png)

### Описание
Диаграмма «36 Architecture Principles Mindmap» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`. На схеме отражено примерно 20 узлов и 5 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: StoragePort, LockPort, MetricsPort, LoggerPort, TracingPort, Infrastructure Adapters.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 36-architecture-principles-mindmap-overview — 36 Architecture Principles Mindmap

![36-architecture-principles-mindmap-overview](views/png/36-architecture-principles-mindmap-overview.png)

### Описание
Диаграмма «36 Architecture Principles Mindmap» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`. На схеме отражено примерно 15 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: DDD Aggregates, 24 Domain Ports, BioETL Architecture, Five-Layer Architecture, Local Only Deployment, Resilience Patterns.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants-dataflow — 39 Medallion Invariants

![39-medallion-invariants-dataflow](views/png/39-medallion-invariants-dataflow.png)

### Описание
Диаграмма «39 Medallion Invariants» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `39-medallion-invariants-full.mermaid`. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: CHECK, INC, BF, RB, E1, I2.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants-domain — 39 Medallion Invariants

![39-medallion-invariants-domain](views/png/39-medallion-invariants-domain.png)

### Описание
Диаграмма «39 Medallion Invariants» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `39-medallion-invariants-full.mermaid`. На схеме отражено примерно 20 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Policy, E2, CHECK, INC, BF, RB.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants-full — Medallion Architecture Invariants (ARCH-007)

![39-medallion-invariants-full](views/png/39-medallion-invariants-full.png)

### Описание
Диаграмма «Medallion Architecture Invariants (ARCH-007)» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §2.1 (Medallion), ARCH-007 clear policy. На схеме отражено примерно 19 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: RunType Enum (domain/types.py), MedallionLifecycleService\n(application/services/medallion_lifecycle.py), INCREMENTAL Path, BACKFILL Path, REBUILD Path, Enforcement. Показательные узлы для быстрого чтения: RunType.INCREMENTAL 'Fetch new data since last run', RunType.BACKFILL 'Re-fetch a date range', RunType.REBUILD 'Full clean rebuild', ❌ DO NOT clear Silver, ❌ DO NOT clear Gold, Silver: merge/upsert (content_hash dedup).

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants-infra — 39 Medallion Invariants

![39-medallion-invariants-infra](views/png/39-medallion-invariants-infra.png)

### Описание
Диаграмма «39 Medallion Invariants» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `39-medallion-invariants-full.mermaid`. На схеме отражено примерно 20 узлов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: Policy, CHECK, INC, BF, RB, E1.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 39-medallion-invariants-overview — 39 Medallion Invariants

![39-medallion-invariants-overview](views/png/39-medallion-invariants-overview.png)

### Описание
Диаграмма «39 Medallion Invariants» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `39-medallion-invariants-full.mermaid`. На схеме отражено примерно 15 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: INC, CHECK, BF, RB, E1, I2.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree-dataflow — 41 Error Classification Tree

![41-error-classification-tree-dataflow](views/png/41-error-classification-tree-dataflow.png)

### Описание
Диаграмма «41 Error Classification Tree» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `41-error-classification-tree-full.mermaid`. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: SCHEMA, HTTP, ERROR, BATCH_FAIL, QUARANTINE2, MISSING.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree-domain — 41 Error Classification Tree

![41-error-classification-tree-domain](views/png/41-error-classification-tree-domain.png)

### Описание
Диаграмма «41 Error Classification Tree» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `41-error-classification-tree-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: ERROR, DOMAIN, DQTHRESH, INFRA, no, classify.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree-full — Error Classification Decision Tree — Full Logic

![41-error-classification-tree-full](views/png/41-error-classification-tree-full.png)

### Описание
Диаграмма «Error Classification Decision Tree — Full Logic» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: RULES.md §3.1 (Error Handling), domain/exceptions/. На схеме отражено примерно 4 узлов и 44 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: HTTP Branch Outcomes, Domain Branch Outcomes, Infrastructure Branch Outcomes, Error Actions. Показательные узлы для быстрого чтения: Error Occurred, [A] RETRY max_attempts: 3 multiplier: 2.0 jitter: MD5-based, [A] FAIL FAST No retry Pipeline terminates ExitCode.PIPELINE_ERROR, [A] BATCH FAIL error_rate > 20% Entire batch rejected Checkpoint NOT saved.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree-infra — 41 Error Classification Tree

![41-error-classification-tree-infra](views/png/41-error-classification-tree-infra.png)

### Описание
Диаграмма «41 Error Classification Tree» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `41-error-classification-tree-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: SCHEMA, HTTP, ERROR, QUARANTINE2, LOCK, LOCKACQ.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 41-error-classification-tree-overview — 41 Error Classification Tree

![41-error-classification-tree-overview](views/png/41-error-classification-tree-overview.png)

### Описание
Диаграмма «41 Error Classification Tree» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `41-error-classification-tree-full.mermaid`. На схеме отражено примерно 5 узлов и 11 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Action Outcomes. Показательные узлы для быстрого чтения: Error Occurred, [A] Retry, [A] Quarantine, [A] Batch Fail, [A] Fail Fast.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment-dataflow — 44 Cross Provider Enrichment

![44-cross-provider-enrichment-dataflow](views/png/44-cross-provider-enrichment-dataflow.png)

### Описание
Диаграмма «44 Cross Provider Enrichment» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`. На схеме отражено примерно 12 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: pmid, CS, CT, CA, ntitle, authors.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment-domain — 44 Cross Provider Enrichment

![44-cross-provider-enrichment-domain](views/png/44-cross-provider-enrichment-domain.png)

### Описание
Диаграмма «44 Cross Provider Enrichment» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CS, CT, pmid, ntitle, authors, CRS.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment-full — Cross-Provider Data Enrichment Flow — Publication

![44-cross-provider-enrichment-full](views/png/44-cross-provider-enrichment-full.png)

### Описание
Диаграмма «Cross-Provider Data Enrichment Flow — Publication» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: ADR-026 (Composite), publication composite pipeline config. На схеме отражено примерно 19 узлов и 18 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: ChEMBL (Seed), CrossRef (Enricher), PubMed (Enricher), OpenAlex (Enricher), Semantic Scholar (Enricher), Merge Phase. Показательные узлы для быстрого чтения: ChemblAdapter /document endpoint, PublicationTransformer, ("Silver chembl/publication"), CrossRefAdapter /works?filter=doi:..., CrossRefPublicationTransformer, ("Silver crossref/publication").

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment-infra — 44 Cross Provider Enrichment

![44-cross-provider-enrichment-infra](views/png/44-cross-provider-enrichment-infra.png)

### Описание
Диаграмма «44 Cross Provider Enrichment» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`. На схеме отражено примерно 20 узлов и 16 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: pmid, pub_type, CS, CT, CA, ntitle.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 44-cross-provider-enrichment-overview — 44 Cross Provider Enrichment

![44-cross-provider-enrichment-overview](views/png/44-cross-provider-enrichment-overview.png)

### Описание
Диаграмма «44 Cross Provider Enrichment» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`. На схеме отражено примерно 15 узлов и 10 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer. Показательные узлы для быстрого чтения: pmid, CT, CS, CRT, CRS, PMT.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution-dataflow — 46 Yaml Config Resolution

![46-yaml-config-resolution-dataflow](views/png/46-yaml-config-resolution-dataflow.png)

### Описание
Диаграмма «46 Yaml Config Resolution» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`. На схеме отражено примерно 12 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: PIPELINE_CONFIG, TABLE_CONFIG, dq_config_file, override, PIPELINE, PIPELINE_YAML_CFG.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution-domain — 46 Yaml Config Resolution

![46-yaml-config-resolution-domain](views/png/46-yaml-config-resolution-domain.png)

### Описание
Диаграмма «46 Yaml Config Resolution» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`. На схеме отражено примерно 20 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Composition Layer. Показательные узлы для быстрого чтения: PIPELINE_CONFIG, TABLE_CONFIG, dq_config_file, DQ_DEFAULTS, DQ_ENTITY, DQ_INLINE.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution-full — YAML Configuration Resolution Chain

![46-yaml-config-resolution-full](views/png/46-yaml-config-resolution-full.png)

### Описание
Диаграмма «YAML Configuration Resolution Chain» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: infrastructure/config_loader.py, infrastructure/config/, domain/config/. На схеме отражено примерно 27 узлов и 27 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: YAML File Hierarchy, DQ Config Hierarchy (DQConfigLoader), Filter Config Hierarchy (FilterConfigLoader), Infrastructure Config Loaders, Domain Config Objects (Frozen), Pydantic Validation Layer. Показательные узлы для быстрого чтения: configs/base/pipeline.yaml (global defaults), configs/providers/{provider}.yaml (provider defaults), configs/entities/{provider}/{entity}.yaml (unified entity config), configs/providers/{provider}.yaml (source config), configs/base/quality.yaml (global DQ defaults), configs/providers/{provider}.yaml#quality (provider DQ).

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-27`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution-infra — 46 Yaml Config Resolution

![46-yaml-config-resolution-infra](views/png/46-yaml-config-resolution-infra.png)

### Описание
Диаграмма «46 Yaml Config Resolution» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`. На схеме отражено примерно 20 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer, Composition Layer. Показательные узлы для быстрого чтения: dq_config_file, DQ_CONFIG_FILE, FILTER_CONFIG_FILE, override, PIPELINE_CONFIG, TABLE_CONFIG.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 46-yaml-config-resolution-overview — 46 Yaml Config Resolution

![46-yaml-config-resolution-overview](views/png/46-yaml-config-resolution-overview.png)

### Описание
Диаграмма «46 Yaml Config Resolution» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`. На схеме отражено примерно 15 узлов и 4 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Composition Layer. Показательные узлы для быстрого чтения: dq_config_file, override, PIPELINE_CONFIG, TABLE_CONFIG, DQ_ENTITY, PIPELINE.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle-dataflow — 48 Composite Phase Lifecycle

![48-composite-phase-lifecycle-dataflow](views/png/48-composite-phase-lifecycle-dataflow.png)

### Описание
Диаграмма «48 Composite Phase Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`. На схеме отражено примерно 12 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CompositePipelineState, ErrorType (CRITICAL/RECOVERABLE/DQ), KeyExtractorService, Enrichment Plan, Merge Plan, Bronze: seed dataset.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle-domain — 48 Composite Phase Lifecycle

![48-composite-phase-lifecycle-domain](views/png/48-composite-phase-lifecycle-domain.png)

### Описание
Диаграмма «48 Composite Phase Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`. На схеме отражено примерно 11 узлов и 12 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer. Показательные узлы для быстрого чтения: NOT_STARTED, SEED_RUNNING, SEED_COMPLETED, DEPENDENCIES_RUNNING, DEPENDENCIES_COMPLETED, ENRICHING.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle-full — Composite Pipeline Phase Lifecycle (FSM)

![48-composite-phase-lifecycle-full](views/png/48-composite-phase-lifecycle-full.png)

### Описание
Диаграмма «Composite Pipeline Phase Lifecycle (FSM)» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате диаграмма состояний (state diagram) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: domain/composite/state.py, application/composite/fsm_helper.py.

### Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle-infra — 48 Composite Phase Lifecycle

![48-composite-phase-lifecycle-infra](views/png/48-composite-phase-lifecycle-infra.png)

### Описание
Диаграмма «48 Composite Phase Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`. На схеме отражено примерно 9 узлов и 9 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: CompositePipelineState, CompositePipelineRunner, PhaseDispatcher, PipelineRunner (seed), DependencyCoordinator, EnrichmentCoordinator.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 48-composite-phase-lifecycle-overview — 48 Composite Phase Lifecycle

![48-composite-phase-lifecycle-overview](views/png/48-composite-phase-lifecycle-overview.png)

### Описание
Диаграмма «48 Composite Phase Lifecycle» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`. На схеме отражено примерно 9 узлов и 7 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: SEED, DEPENDENCIES, ENRICHING, MERGING, COMPLETED, FAILED.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`

\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy-dataflow — 50 Exception Hierarchy

![50-exception-hierarchy-dataflow](views/png/50-exception-hierarchy-dataflow.png)

### Описание
Диаграмма «50 Exception Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Data-Flow. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`. На схеме отражено примерно 12 узлов и 8 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DELTA_SCHEMA_V, BRONZE_VALID, record_id, MERGE_CONFLICT, EXT_SERVICE, DELTA_TX.

### Метаданные
- Тип: `flowchart`
- Представление: `Data-Flow`

\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy-domain — 50 Exception Hierarchy

![50-exception-hierarchy-domain](views/png/50-exception-hierarchy-domain.png)

### Описание
Диаграмма «50 Exception Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Domain-Focus. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`. На схеме отражено примерно 20 узлов и 21 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: DQ_ERROR, POLICY_VIOLATION, METRICS_ERROR, port, INFRA_ERROR, last_error.

### Метаданные
- Тип: `flowchart`
- Представление: `Domain-Focus`

\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy-full — Exception Hierarchy — Full Tree

![50-exception-hierarchy-full](views/png/50-exception-hierarchy-full.png)

### Описание
Диаграмма «Exception Hierarchy — Full Tree» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». Тип представления: Full. Родительская диаграмма: `(root)`. В комментариях исходника зафиксирован фокус диаграммы: domain/exceptions/ (base, network, validation, internal, infrastructure, data_quality). На схеме отражено примерно 6 узлов и 50 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Показательные узлы для быстрого чтения: Exception (Python built-in), BioETLError domain/exceptions/base.py error_type: ErrorType context: dict, ErrorClassifier domain/error_classifier.py .classify(error) → ErrorType, Action: ABORT Pipeline stops immediately PipelineRunState → FAILED, Action: RETRY Exponential backoff Max retries from AdapterConfig, Action: QUARANTINE Record → QuarantineEntry Pipeline continues.

### Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата: `2026-02-24`
- Представление: `Full`

\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy-infra — 50 Exception Hierarchy

![50-exception-hierarchy-infra](views/png/50-exception-hierarchy-infra.png)

### Описание
Диаграмма «50 Exception Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Infrastructure-Mapping. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`. На схеме отражено примерно 20 узлов и 22 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: METRICS_ERROR, DELTA_SCHEMA_V, DQ_ERROR, VALIDATION, EXT_SERVICE, STORAGE_ERR.

### Метаданные
- Тип: `flowchart`
- Представление: `Infrastructure-Mapping`

\newpage

<div style="page-break-before: always;"></div>

## 50-exception-hierarchy-overview — 50 Exception Hierarchy

![50-exception-hierarchy-overview](views/png/50-exception-hierarchy-overview.png)

### Описание
Диаграмма «50 Exception Hierarchy» из views-набора представляет фокусированный срез родительской диаграммы для точечного анализа. Она представлена в формате блок-схема потоков (flowchart). Тип представления: Overview. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`. На схеме отражено примерно 15 узлов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые блоки/подграфы: Domain Layer, Application Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: INVALID_STATE, POLICY_VIOLATION, run_id, BIOETL, CRITICAL, RECOVERABLE.

### Метаданные
- Тип: `flowchart`
- Представление: `Overview`
