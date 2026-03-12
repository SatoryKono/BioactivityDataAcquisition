# BioETL Views Diagrams With Descriptions

- Generated: 2026-03-12T12:56:40
- Diagram count: 162

## Table of Contents

- [00-legend](#00-legend)
- [01-full-system-component-dataflow](#01-full-system-component-dataflow)
- [01-full-system-component-domain](#01-full-system-component-domain)
- [01-full-system-component-full](#01-full-system-component-full)
- [01-full-system-component-infra](#01-full-system-component-infra)
- [01-full-system-component-overview](#01-full-system-component-overview)
- [01-high-level-dataflow](#01-high-level-dataflow)
- [01-high-level-domain](#01-high-level-domain)
- [01-high-level-full](#01-high-level-full)
- [01-high-level-infra](#01-high-level-infra)
- [01-high-level-overview](#01-high-level-overview)
- [02-medallion-dataflow](#02-medallion-dataflow)
- [02-medallion-domain](#02-medallion-domain)
- [02-medallion-full](#02-medallion-full)
- [02-medallion-infra](#02-medallion-infra)
- [02-medallion-overview](#02-medallion-overview)
- [03-medallion-data-flow-full](#03-medallion-data-flow-full)
- [03-medallion-data-flow-overview](#03-medallion-data-flow-overview)
- [04-domain-layer-class-diagram-dataflow](#04-domain-layer-class-diagram-dataflow)
- [04-domain-layer-class-diagram-domain](#04-domain-layer-class-diagram-domain)
- [04-domain-layer-class-diagram-full](#04-domain-layer-class-diagram-full)
- [04-domain-layer-class-diagram-infra](#04-domain-layer-class-diagram-infra)
- [04-domain-layer-class-diagram-overview](#04-domain-layer-class-diagram-overview)
- [05-layers-interaction-dataflow](#05-layers-interaction-dataflow)
- [05-layers-interaction-domain](#05-layers-interaction-domain)
- [05-layers-interaction-full](#05-layers-interaction-full)
- [05-layers-interaction-infra](#05-layers-interaction-infra)
- [05-layers-interaction-overview](#05-layers-interaction-overview)
- [05-pipeline-lifecycle-states-dataflow](#05-pipeline-lifecycle-states-dataflow)
- [05-pipeline-lifecycle-states-domain](#05-pipeline-lifecycle-states-domain)
- [05-pipeline-lifecycle-states-full](#05-pipeline-lifecycle-states-full)
- [05-pipeline-lifecycle-states-infra](#05-pipeline-lifecycle-states-infra)
- [05-pipeline-lifecycle-states-overview](#05-pipeline-lifecycle-states-overview)
- [06-application-layer-class-diagram-dataflow](#06-application-layer-class-diagram-dataflow)
- [06-application-layer-class-diagram-domain](#06-application-layer-class-diagram-domain)
- [06-application-layer-class-diagram-full](#06-application-layer-class-diagram-full)
- [06-application-layer-class-diagram-infra](#06-application-layer-class-diagram-infra)
- [06-application-layer-class-diagram-overview](#06-application-layer-class-diagram-overview)
- [07-circuit-breaker-states-dataflow](#07-circuit-breaker-states-dataflow)
- [07-circuit-breaker-states-domain](#07-circuit-breaker-states-domain)
- [07-circuit-breaker-states-full](#07-circuit-breaker-states-full)
- [07-circuit-breaker-states-infra](#07-circuit-breaker-states-infra)
- [07-circuit-breaker-states-overview](#07-circuit-breaker-states-overview)
- [08-complete-etl-workflow-dataflow](#08-complete-etl-workflow-dataflow)
- [08-complete-etl-workflow-domain](#08-complete-etl-workflow-domain)
- [08-complete-etl-workflow-full](#08-complete-etl-workflow-full)
- [08-complete-etl-workflow-infra](#08-complete-etl-workflow-infra)
- [08-complete-etl-workflow-overview](#08-complete-etl-workflow-overview)
- [08-domain-ddd-dataflow](#08-domain-ddd-dataflow)
- [08-domain-ddd-domain](#08-domain-ddd-domain)
- [08-domain-ddd-full](#08-domain-ddd-full)
- [08-domain-ddd-infra](#08-domain-ddd-infra)
- [08-domain-ddd-overview](#08-domain-ddd-overview)
- [10-infrastructure-layer-class-diagram-dataflow](#10-infrastructure-layer-class-diagram-dataflow)
- [10-infrastructure-layer-class-diagram-domain](#10-infrastructure-layer-class-diagram-domain)
- [10-infrastructure-layer-class-diagram-full](#10-infrastructure-layer-class-diagram-full)
- [10-infrastructure-layer-class-diagram-infra](#10-infrastructure-layer-class-diagram-infra)
- [10-infrastructure-layer-class-diagram-overview](#10-infrastructure-layer-class-diagram-overview)
- [12-local-deployment-architecture-dataflow](#12-local-deployment-architecture-dataflow)
- [12-local-deployment-architecture-domain](#12-local-deployment-architecture-domain)
- [12-local-deployment-architecture-full](#12-local-deployment-architecture-full)
- [12-local-deployment-architecture-infra](#12-local-deployment-architecture-infra)
- [12-local-deployment-architecture-overview](#12-local-deployment-architecture-overview)
- [13-port-protocol-contracts-full](#13-port-protocol-contracts-full)
- [13-port-protocol-contracts-overview](#13-port-protocol-contracts-overview)
- [14-provider-health-states-dataflow](#14-provider-health-states-dataflow)
- [14-provider-health-states-domain](#14-provider-health-states-domain)
- [14-provider-health-states-full](#14-provider-health-states-full)
- [14-provider-health-states-infra](#14-provider-health-states-infra)
- [14-provider-health-states-overview](#14-provider-health-states-overview)
- [15-dq-check-workflow-dataflow](#15-dq-check-workflow-dataflow)
- [15-dq-check-workflow-domain](#15-dq-check-workflow-domain)
- [15-dq-check-workflow-full](#15-dq-check-workflow-full)
- [15-dq-check-workflow-infra](#15-dq-check-workflow-infra)
- [15-dq-check-workflow-overview](#15-dq-check-workflow-overview)
- [16-transformer-hierarchy-full](#16-transformer-hierarchy-full)
- [16-transformer-hierarchy-overview](#16-transformer-hierarchy-overview)
- [21-activity-entity-data-flow-dataflow](#21-activity-entity-data-flow-dataflow)
- [21-activity-entity-data-flow-domain](#21-activity-entity-data-flow-domain)
- [21-activity-entity-data-flow-full](#21-activity-entity-data-flow-full)
- [21-activity-entity-data-flow-infra](#21-activity-entity-data-flow-infra)
- [21-activity-entity-data-flow-overview](#21-activity-entity-data-flow-overview)
- [26-hexagonal-ports-adapters-dataflow](#26-hexagonal-ports-adapters-dataflow)
- [26-hexagonal-ports-adapters-domain](#26-hexagonal-ports-adapters-domain)
- [26-hexagonal-ports-adapters-full](#26-hexagonal-ports-adapters-full)
- [26-hexagonal-ports-adapters-infra](#26-hexagonal-ports-adapters-infra)
- [26-hexagonal-ports-adapters-overview](#26-hexagonal-ports-adapters-overview)
- [28-composition-root-di-graph-dataflow](#28-composition-root-di-graph-dataflow)
- [28-composition-root-di-graph-domain](#28-composition-root-di-graph-domain)
- [28-composition-root-di-graph-full](#28-composition-root-di-graph-full)
- [28-composition-root-di-graph-infra](#28-composition-root-di-graph-infra)
- [28-composition-root-di-graph-overview](#28-composition-root-di-graph-overview)
- [29-composite-pipeline-workflow-dataflow](#29-composite-pipeline-workflow-dataflow)
- [29-composite-pipeline-workflow-domain](#29-composite-pipeline-workflow-domain)
- [29-composite-pipeline-workflow-full](#29-composite-pipeline-workflow-full)
- [29-composite-pipeline-workflow-infra](#29-composite-pipeline-workflow-infra)
- [29-composite-pipeline-workflow-overview](#29-composite-pipeline-workflow-overview)
- [30-port-adapter-mapping-dataflow](#30-port-adapter-mapping-dataflow)
- [30-port-adapter-mapping-domain](#30-port-adapter-mapping-domain)
- [30-port-adapter-mapping-full](#30-port-adapter-mapping-full)
- [30-port-adapter-mapping-infra](#30-port-adapter-mapping-infra)
- [30-port-adapter-mapping-overview](#30-port-adapter-mapping-overview)
- [31-pipeline-run-lifecycle-dataflow](#31-pipeline-run-lifecycle-dataflow)
- [31-pipeline-run-lifecycle-domain](#31-pipeline-run-lifecycle-domain)
- [31-pipeline-run-lifecycle-full](#31-pipeline-run-lifecycle-full)
- [31-pipeline-run-lifecycle-infra](#31-pipeline-run-lifecycle-infra)
- [31-pipeline-run-lifecycle-overview](#31-pipeline-run-lifecycle-overview)
- [32-single-record-journey-dataflow](#32-single-record-journey-dataflow)
- [32-single-record-journey-domain](#32-single-record-journey-domain)
- [32-single-record-journey-full](#32-single-record-journey-full)
- [32-single-record-journey-infra](#32-single-record-journey-infra)
- [32-single-record-journey-overview](#32-single-record-journey-overview)
- [33-cli-run-interaction-dataflow](#33-cli-run-interaction-dataflow)
- [33-cli-run-interaction-domain](#33-cli-run-interaction-domain)
- [33-cli-run-interaction-full](#33-cli-run-interaction-full)
- [33-cli-run-interaction-infra](#33-cli-run-interaction-infra)
- [33-cli-run-interaction-overview](#33-cli-run-interaction-overview)
- [34-batch-processing-flow-dataflow](#34-batch-processing-flow-dataflow)
- [34-batch-processing-flow-domain](#34-batch-processing-flow-domain)
- [34-batch-processing-flow-full](#34-batch-processing-flow-full)
- [34-batch-processing-flow-infra](#34-batch-processing-flow-infra)
- [34-batch-processing-flow-overview](#34-batch-processing-flow-overview)
- [35-bootstrap-sequence-dataflow](#35-bootstrap-sequence-dataflow)
- [35-bootstrap-sequence-domain](#35-bootstrap-sequence-domain)
- [35-bootstrap-sequence-full](#35-bootstrap-sequence-full)
- [35-bootstrap-sequence-infra](#35-bootstrap-sequence-infra)
- [35-bootstrap-sequence-overview](#35-bootstrap-sequence-overview)
- [36-architecture-principles-mindmap-dataflow](#36-architecture-principles-mindmap-dataflow)
- [36-architecture-principles-mindmap-domain](#36-architecture-principles-mindmap-domain)
- [36-architecture-principles-mindmap-full](#36-architecture-principles-mindmap-full)
- [36-architecture-principles-mindmap-infra](#36-architecture-principles-mindmap-infra)
- [36-architecture-principles-mindmap-overview](#36-architecture-principles-mindmap-overview)
- [39-medallion-invariants-dataflow](#39-medallion-invariants-dataflow)
- [39-medallion-invariants-domain](#39-medallion-invariants-domain)
- [39-medallion-invariants-full](#39-medallion-invariants-full)
- [39-medallion-invariants-infra](#39-medallion-invariants-infra)
- [39-medallion-invariants-overview](#39-medallion-invariants-overview)
- [41-error-classification-tree-dataflow](#41-error-classification-tree-dataflow)
- [41-error-classification-tree-domain](#41-error-classification-tree-domain)
- [41-error-classification-tree-full](#41-error-classification-tree-full)
- [41-error-classification-tree-infra](#41-error-classification-tree-infra)
- [41-error-classification-tree-overview](#41-error-classification-tree-overview)
- [44-cross-provider-enrichment-dataflow](#44-cross-provider-enrichment-dataflow)
- [44-cross-provider-enrichment-domain](#44-cross-provider-enrichment-domain)
- [44-cross-provider-enrichment-full](#44-cross-provider-enrichment-full)
- [44-cross-provider-enrichment-infra](#44-cross-provider-enrichment-infra)
- [44-cross-provider-enrichment-overview](#44-cross-provider-enrichment-overview)
- [46-yaml-config-resolution-dataflow](#46-yaml-config-resolution-dataflow)
- [46-yaml-config-resolution-domain](#46-yaml-config-resolution-domain)
- [46-yaml-config-resolution-full](#46-yaml-config-resolution-full)
- [46-yaml-config-resolution-infra](#46-yaml-config-resolution-infra)
- [46-yaml-config-resolution-overview](#46-yaml-config-resolution-overview)
- [48-composite-phase-lifecycle-dataflow](#48-composite-phase-lifecycle-dataflow)
- [48-composite-phase-lifecycle-domain](#48-composite-phase-lifecycle-domain)
- [48-composite-phase-lifecycle-full](#48-composite-phase-lifecycle-full)
- [48-composite-phase-lifecycle-infra](#48-composite-phase-lifecycle-infra)
- [48-composite-phase-lifecycle-overview](#48-composite-phase-lifecycle-overview)
- [50-exception-hierarchy-dataflow](#50-exception-hierarchy-dataflow)
- [50-exception-hierarchy-domain](#50-exception-hierarchy-domain)
- [50-exception-hierarchy-full](#50-exception-hierarchy-full)
- [50-exception-hierarchy-infra](#50-exception-hierarchy-infra)
- [50-exception-hierarchy-overview](#50-exception-hierarchy-overview)

---

## 00-legend

![00-legend](views/png/00-legend.png)

- Исходная диаграмма: `mmd-diagrams/views/00-legend.mermaid`

## Описание
Views-диаграмма «00 Legend» (уровень: Legend) представлена в формате flowchart. Родительская диаграмма: `(root)`.

## Метаданные
- Тип: `flowchart`
- Вид: `Legend`

<div style="page-break-after: always;"></div>

## 01-full-system-component-dataflow

![01-full-system-component-dataflow](views/png/01-full-system-component-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/01-full-system-component-dataflow.mermaid`

## Описание
Views-диаграмма «01 Full System Component Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `01-full-system-component-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 01-full-system-component-domain

![01-full-system-component-domain](views/png/01-full-system-component-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/01-full-system-component-domain.mermaid`

## Описание
Views-диаграмма «01 Full System Component Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `01-full-system-component-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 01-full-system-component-full

![01-full-system-component-full](views/png/01-full-system-component-full.png)

- Исходная диаграмма: `mmd-diagrams/views/01-full-system-component-full.mermaid`

## Описание
Views-диаграмма «Full System Component Diagram» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Five-Layer Architecture), §1.2 (Ports & Adapters).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 01-full-system-component-infra

![01-full-system-component-infra](views/png/01-full-system-component-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/01-full-system-component-infra.mermaid`

## Описание
Views-диаграмма «01 Full System Component Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `01-full-system-component-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 01-full-system-component-overview

![01-full-system-component-overview](views/png/01-full-system-component-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/01-full-system-component-overview.mermaid`

## Описание
Views-диаграмма «01 Full System Component Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `01-full-system-component-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 01-high-level-dataflow

![01-high-level-dataflow](views/png/01-high-level-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/01-high-level-dataflow.mermaid`

## Описание
Views-диаграмма «01 High Level Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `01-high-level-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 01-high-level-domain

![01-high-level-domain](views/png/01-high-level-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/01-high-level-domain.mermaid`

## Описание
Views-диаграмма «01 High Level Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `01-high-level-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 01-high-level-full

![01-high-level-full](views/png/01-high-level-full.png)

- Исходная диаграмма: `mmd-diagrams/views/01-high-level-full.mermaid`

## Описание
Views-диаграмма «High-Level System Architecture» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Five-Layer Architecture).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 01-high-level-infra

![01-high-level-infra](views/png/01-high-level-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/01-high-level-infra.mermaid`

## Описание
Views-диаграмма «01 High Level Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `01-high-level-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 01-high-level-overview

![01-high-level-overview](views/png/01-high-level-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/01-high-level-overview.mermaid`

## Описание
Views-диаграмма «01 High Level Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `01-high-level-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 02-medallion-dataflow

![02-medallion-dataflow](views/png/02-medallion-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/02-medallion-dataflow.mermaid`

## Описание
Views-диаграмма «02 Medallion Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `02-medallion-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 02-medallion-domain

![02-medallion-domain](views/png/02-medallion-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/02-medallion-domain.mermaid`

## Описание
Views-диаграмма «02 Medallion Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `02-medallion-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 02-medallion-full

![02-medallion-full](views/png/02-medallion-full.png)

- Исходная диаграмма: `mmd-diagrams/views/02-medallion-full.mermaid`

## Описание
Views-диаграмма «Medallion Architecture Layers» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.1 (Bronze/Silver/Gold), §2.3 (Quarantine).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 02-medallion-infra

![02-medallion-infra](views/png/02-medallion-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/02-medallion-infra.mermaid`

## Описание
Views-диаграмма «02 Medallion Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `02-medallion-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 02-medallion-overview

![02-medallion-overview](views/png/02-medallion-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/02-medallion-overview.mermaid`

## Описание
Views-диаграмма «02 Medallion Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `02-medallion-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 03-medallion-data-flow-full

![03-medallion-data-flow-full](views/png/03-medallion-data-flow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/03-medallion-data-flow-full.mermaid`

## Описание
Views-диаграмма «03 Medallion Data Flow Full» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `03-medallion-data-flow.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 03-medallion-data-flow-overview

![03-medallion-data-flow-overview](views/png/03-medallion-data-flow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/03-medallion-data-flow-overview.mermaid`

## Описание
Views-диаграмма «03 Medallion Data Flow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `03-medallion-data-flow.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 04-domain-layer-class-diagram-dataflow

![04-domain-layer-class-diagram-dataflow](views/png/04-domain-layer-class-diagram-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/04-domain-layer-class-diagram-dataflow.mermaid`

## Описание
Views-диаграмма «04 Domain Layer Class Diagram Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 04-domain-layer-class-diagram-domain

![04-domain-layer-class-diagram-domain](views/png/04-domain-layer-class-diagram-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/04-domain-layer-class-diagram-domain.mermaid`

## Описание
Views-диаграмма «04 Domain Layer Class Diagram Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 04-domain-layer-class-diagram-full

![04-domain-layer-class-diagram-full](views/png/04-domain-layer-class-diagram-full.png)

- Исходная диаграмма: `mmd-diagrams/views/04-domain-layer-class-diagram-full.mermaid`

## Описание
Views-диаграмма «Domain Layer Class Diagram» (уровень: Full) представлена в формате classDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Domain Layer), §1.2 (Ports), §1.3 (Entities).

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 04-domain-layer-class-diagram-infra

![04-domain-layer-class-diagram-infra](views/png/04-domain-layer-class-diagram-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/04-domain-layer-class-diagram-infra.mermaid`

## Описание
Views-диаграмма «04 Domain Layer Class Diagram Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 04-domain-layer-class-diagram-overview

![04-domain-layer-class-diagram-overview](views/png/04-domain-layer-class-diagram-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/04-domain-layer-class-diagram-overview.mermaid`

## Описание
Views-диаграмма «04 Domain Layer Class Diagram Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `04-domain-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 05-layers-interaction-dataflow

![05-layers-interaction-dataflow](views/png/05-layers-interaction-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/05-layers-interaction-dataflow.mermaid`

## Описание
Views-диаграмма «05 Layers Interaction Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `05-layers-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 05-layers-interaction-domain

![05-layers-interaction-domain](views/png/05-layers-interaction-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/05-layers-interaction-domain.mermaid`

## Описание
Views-диаграмма «05 Layers Interaction Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `05-layers-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 05-layers-interaction-full

![05-layers-interaction-full](views/png/05-layers-interaction-full.png)

- Исходная диаграмма: `mmd-diagrams/views/05-layers-interaction-full.mermaid`

## Описание
Views-диаграмма «Layer Interaction — Hexagonal Architecture» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Layers), §1.2 (Ports & Adapters).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 05-layers-interaction-infra

![05-layers-interaction-infra](views/png/05-layers-interaction-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/05-layers-interaction-infra.mermaid`

## Описание
Views-диаграмма «05 Layers Interaction Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `05-layers-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 05-layers-interaction-overview

![05-layers-interaction-overview](views/png/05-layers-interaction-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/05-layers-interaction-overview.mermaid`

## Описание
Views-диаграмма «05 Layers Interaction Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `05-layers-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 05-pipeline-lifecycle-states-dataflow

![05-pipeline-lifecycle-states-dataflow](views/png/05-pipeline-lifecycle-states-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/05-pipeline-lifecycle-states-dataflow.mermaid`

## Описание
Views-диаграмма «05 Pipeline Lifecycle States Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 05-pipeline-lifecycle-states-domain

![05-pipeline-lifecycle-states-domain](views/png/05-pipeline-lifecycle-states-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/05-pipeline-lifecycle-states-domain.mermaid`

## Описание
Views-диаграмма «05 Pipeline Lifecycle States Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 05-pipeline-lifecycle-states-full

![05-pipeline-lifecycle-states-full](views/png/05-pipeline-lifecycle-states-full.png)

- Исходная диаграмма: `mmd-diagrams/views/05-pipeline-lifecycle-states-full.mermaid`

## Описание
Views-диаграмма «Pipeline Lifecycle State Machine» (уровень: Full) представлена в формате stateDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3 (Pipeline Execution), §3.5 (Graceful Shutdown).

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 05-pipeline-lifecycle-states-infra

![05-pipeline-lifecycle-states-infra](views/png/05-pipeline-lifecycle-states-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/05-pipeline-lifecycle-states-infra.mermaid`

## Описание
Views-диаграмма «05 Pipeline Lifecycle States Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 05-pipeline-lifecycle-states-overview

![05-pipeline-lifecycle-states-overview](views/png/05-pipeline-lifecycle-states-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/05-pipeline-lifecycle-states-overview.mermaid`

## Описание
Views-диаграмма «05 Pipeline Lifecycle States Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `05-pipeline-lifecycle-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 06-application-layer-class-diagram-dataflow

![06-application-layer-class-diagram-dataflow](views/png/06-application-layer-class-diagram-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/06-application-layer-class-diagram-dataflow.mermaid`

## Описание
Views-диаграмма «06 Application Layer Class Diagram Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 06-application-layer-class-diagram-domain

![06-application-layer-class-diagram-domain](views/png/06-application-layer-class-diagram-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/06-application-layer-class-diagram-domain.mermaid`

## Описание
Views-диаграмма «06 Application Layer Class Diagram Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 06-application-layer-class-diagram-full

![06-application-layer-class-diagram-full](views/png/06-application-layer-class-diagram-full.png)

- Исходная диаграмма: `mmd-diagrams/views/06-application-layer-class-diagram-full.mermaid`

## Описание
Views-диаграмма «Application Layer Class Diagram» (уровень: Full) представлена в формате classDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Application Layer), §3 (Pipeline Execution).

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 06-application-layer-class-diagram-infra

![06-application-layer-class-diagram-infra](views/png/06-application-layer-class-diagram-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/06-application-layer-class-diagram-infra.mermaid`

## Описание
Views-диаграмма «06 Application Layer Class Diagram Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 06-application-layer-class-diagram-overview

![06-application-layer-class-diagram-overview](views/png/06-application-layer-class-diagram-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/06-application-layer-class-diagram-overview.mermaid`

## Описание
Views-диаграмма «06 Application Layer Class Diagram Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `06-application-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 07-circuit-breaker-states-dataflow

![07-circuit-breaker-states-dataflow](views/png/07-circuit-breaker-states-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/07-circuit-breaker-states-dataflow.mermaid`

## Описание
Views-диаграмма «07 Circuit Breaker States Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 07-circuit-breaker-states-domain

![07-circuit-breaker-states-domain](views/png/07-circuit-breaker-states-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/07-circuit-breaker-states-domain.mermaid`

## Описание
Views-диаграмма «07 Circuit Breaker States Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 07-circuit-breaker-states-full

![07-circuit-breaker-states-full](views/png/07-circuit-breaker-states-full.png)

- Исходная диаграмма: `mmd-diagrams/views/07-circuit-breaker-states-full.mermaid`

## Описание
Views-диаграмма «Circuit Breaker State Machine» (уровень: Full) представлена в формате stateDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3.6 (Resilience), ADR-007.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 07-circuit-breaker-states-infra

![07-circuit-breaker-states-infra](views/png/07-circuit-breaker-states-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/07-circuit-breaker-states-infra.mermaid`

## Описание
Views-диаграмма «07 Circuit Breaker States Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 07-circuit-breaker-states-overview

![07-circuit-breaker-states-overview](views/png/07-circuit-breaker-states-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/07-circuit-breaker-states-overview.mermaid`

## Описание
Views-диаграмма «07 Circuit Breaker States Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `07-circuit-breaker-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 08-complete-etl-workflow-dataflow

![08-complete-etl-workflow-dataflow](views/png/08-complete-etl-workflow-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/08-complete-etl-workflow-dataflow.mermaid`

## Описание
Views-диаграмма «08 Complete Etl Workflow Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 08-complete-etl-workflow-domain

![08-complete-etl-workflow-domain](views/png/08-complete-etl-workflow-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/08-complete-etl-workflow-domain.mermaid`

## Описание
Views-диаграмма «08 Complete Etl Workflow Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 08-complete-etl-workflow-full

![08-complete-etl-workflow-full](views/png/08-complete-etl-workflow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/08-complete-etl-workflow-full.mermaid`

## Описание
Views-диаграмма «Complete ETL Workflow (6 Phases)» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3 (Pipeline Execution), §3.2 (Preflight), §3.4 (Postrun).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 08-complete-etl-workflow-infra

![08-complete-etl-workflow-infra](views/png/08-complete-etl-workflow-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/08-complete-etl-workflow-infra.mermaid`

## Описание
Views-диаграмма «08 Complete Etl Workflow Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 08-complete-etl-workflow-overview

![08-complete-etl-workflow-overview](views/png/08-complete-etl-workflow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/08-complete-etl-workflow-overview.mermaid`

## Описание
Views-диаграмма «08 Complete Etl Workflow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `08-complete-etl-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 08-domain-ddd-dataflow

![08-domain-ddd-dataflow](views/png/08-domain-ddd-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/08-domain-ddd-dataflow.mermaid`

## Описание
Views-диаграмма «08 Domain Ddd Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `08-domain-ddd-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 08-domain-ddd-domain

![08-domain-ddd-domain](views/png/08-domain-ddd-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/08-domain-ddd-domain.mermaid`

## Описание
Views-диаграмма «08 Domain Ddd Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `08-domain-ddd-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 08-domain-ddd-full

![08-domain-ddd-full](views/png/08-domain-ddd-full.png)

- Исходная диаграмма: `mmd-diagrams/views/08-domain-ddd-full.mermaid`

## Описание
Views-диаграмма «Domain Layer — DDD Components» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Domain Layer), §1.3 (DDD Aggregates), ADR-021.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 08-domain-ddd-infra

![08-domain-ddd-infra](views/png/08-domain-ddd-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/08-domain-ddd-infra.mermaid`

## Описание
Views-диаграмма «08 Domain Ddd Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `08-domain-ddd-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 08-domain-ddd-overview

![08-domain-ddd-overview](views/png/08-domain-ddd-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/08-domain-ddd-overview.mermaid`

## Описание
Views-диаграмма «08 Domain Ddd Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `08-domain-ddd-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 10-infrastructure-layer-class-diagram-dataflow

![10-infrastructure-layer-class-diagram-dataflow](views/png/10-infrastructure-layer-class-diagram-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/10-infrastructure-layer-class-diagram-dataflow.mermaid`

## Описание
Views-диаграмма «10 Infrastructure Layer Class Diagram Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 10-infrastructure-layer-class-diagram-domain

![10-infrastructure-layer-class-diagram-domain](views/png/10-infrastructure-layer-class-diagram-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/10-infrastructure-layer-class-diagram-domain.mermaid`

## Описание
Views-диаграмма «10 Infrastructure Layer Class Diagram Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 10-infrastructure-layer-class-diagram-full

![10-infrastructure-layer-class-diagram-full](views/png/10-infrastructure-layer-class-diagram-full.png)

- Исходная диаграмма: `mmd-diagrams/views/10-infrastructure-layer-class-diagram-full.mermaid`

## Описание
Views-диаграмма «Infrastructure Layer Class Diagram» (уровень: Full) представлена в формате classDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Infrastructure Layer), §3.6 (Resilience).

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 10-infrastructure-layer-class-diagram-infra

![10-infrastructure-layer-class-diagram-infra](views/png/10-infrastructure-layer-class-diagram-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/10-infrastructure-layer-class-diagram-infra.mermaid`

## Описание
Views-диаграмма «10 Infrastructure Layer Class Diagram Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 10-infrastructure-layer-class-diagram-overview

![10-infrastructure-layer-class-diagram-overview](views/png/10-infrastructure-layer-class-diagram-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/10-infrastructure-layer-class-diagram-overview.mermaid`

## Описание
Views-диаграмма «10 Infrastructure Layer Class Diagram Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `10-infrastructure-layer-class-diagram-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 12-local-deployment-architecture-dataflow

![12-local-deployment-architecture-dataflow](views/png/12-local-deployment-architecture-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/12-local-deployment-architecture-dataflow.mermaid`

## Описание
Views-диаграмма «12 Local Deployment Architecture Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 12-local-deployment-architecture-domain

![12-local-deployment-architecture-domain](views/png/12-local-deployment-architecture-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/12-local-deployment-architecture-domain.mermaid`

## Описание
Views-диаграмма «12 Local Deployment Architecture Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 12-local-deployment-architecture-full

![12-local-deployment-architecture-full](views/png/12-local-deployment-architecture-full.png)

- Исходная диаграмма: `mmd-diagrams/views/12-local-deployment-architecture-full.mermaid`

## Описание
Views-диаграмма «Local Deployment Architecture» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §5.6 (Deployment), ADR-010 (Local-Only).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 12-local-deployment-architecture-infra

![12-local-deployment-architecture-infra](views/png/12-local-deployment-architecture-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/12-local-deployment-architecture-infra.mermaid`

## Описание
Views-диаграмма «12 Local Deployment Architecture Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 12-local-deployment-architecture-overview

![12-local-deployment-architecture-overview](views/png/12-local-deployment-architecture-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/12-local-deployment-architecture-overview.mermaid`

## Описание
Views-диаграмма «12 Local Deployment Architecture Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `12-local-deployment-architecture-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 13-port-protocol-contracts-full

![13-port-protocol-contracts-full](views/png/13-port-protocol-contracts-full.png)

- Исходная диаграмма: `mmd-diagrams/views/13-port-protocol-contracts-full.mermaid`

## Описание
Views-диаграмма «13 Port Protocol Contracts Full» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `13-port-protocol-contracts.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 13-port-protocol-contracts-overview

![13-port-protocol-contracts-overview](views/png/13-port-protocol-contracts-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/13-port-protocol-contracts-overview.mermaid`

## Описание
Views-диаграмма «13 Port Protocol Contracts Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `13-port-protocol-contracts.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 14-provider-health-states-dataflow

![14-provider-health-states-dataflow](views/png/14-provider-health-states-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/14-provider-health-states-dataflow.mermaid`

## Описание
Views-диаграмма «14 Provider Health States Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `14-provider-health-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 14-provider-health-states-domain

![14-provider-health-states-domain](views/png/14-provider-health-states-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/14-provider-health-states-domain.mermaid`

## Описание
Views-диаграмма «14 Provider Health States Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `14-provider-health-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 14-provider-health-states-full

![14-provider-health-states-full](views/png/14-provider-health-states-full.png)

- Исходная диаграмма: `mmd-diagrams/views/14-provider-health-states-full.mermaid`

## Описание
Views-диаграмма «Provider Health State Machine» (уровень: Full) представлена в формате stateDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3.6 (Resilience), §4 (Provider Specifications).

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 14-provider-health-states-infra

![14-provider-health-states-infra](views/png/14-provider-health-states-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/14-provider-health-states-infra.mermaid`

## Описание
Views-диаграмма «14 Provider Health States Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `14-provider-health-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 14-provider-health-states-overview

![14-provider-health-states-overview](views/png/14-provider-health-states-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/14-provider-health-states-overview.mermaid`

## Описание
Views-диаграмма «14 Provider Health States Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `14-provider-health-states-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 15-dq-check-workflow-dataflow

![15-dq-check-workflow-dataflow](views/png/15-dq-check-workflow-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/15-dq-check-workflow-dataflow.mermaid`

## Описание
Views-диаграмма «15 Dq Check Workflow Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 15-dq-check-workflow-domain

![15-dq-check-workflow-domain](views/png/15-dq-check-workflow-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/15-dq-check-workflow-domain.mermaid`

## Описание
Views-диаграмма «15 Dq Check Workflow Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 15-dq-check-workflow-full

![15-dq-check-workflow-full](views/png/15-dq-check-workflow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/15-dq-check-workflow-full.mermaid`

## Описание
Views-диаграмма «Data Quality Check Workflow» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3.1 (DQ Checks), §2.3 (Quarantine).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 15-dq-check-workflow-infra

![15-dq-check-workflow-infra](views/png/15-dq-check-workflow-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/15-dq-check-workflow-infra.mermaid`

## Описание
Views-диаграмма «15 Dq Check Workflow Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 15-dq-check-workflow-overview

![15-dq-check-workflow-overview](views/png/15-dq-check-workflow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/15-dq-check-workflow-overview.mermaid`

## Описание
Views-диаграмма «15 Dq Check Workflow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `15-dq-check-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 16-transformer-hierarchy-full

![16-transformer-hierarchy-full](views/png/16-transformer-hierarchy-full.png)

- Исходная диаграмма: `mmd-diagrams/views/16-transformer-hierarchy-full.mermaid`

## Описание
Views-диаграмма «16 Transformer Hierarchy Full» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `16-transformer-hierarchy.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 16-transformer-hierarchy-overview

![16-transformer-hierarchy-overview](views/png/16-transformer-hierarchy-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/16-transformer-hierarchy-overview.mermaid`

## Описание
Views-диаграмма «16 Transformer Hierarchy Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `16-transformer-hierarchy.mmd`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 21-activity-entity-data-flow-dataflow

![21-activity-entity-data-flow-dataflow](views/png/21-activity-entity-data-flow-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/21-activity-entity-data-flow-dataflow.mermaid`

## Описание
Views-диаграмма «21 Activity Entity Data Flow Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 21-activity-entity-data-flow-domain

![21-activity-entity-data-flow-domain](views/png/21-activity-entity-data-flow-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/21-activity-entity-data-flow-domain.mermaid`

## Описание
Views-диаграмма «21 Activity Entity Data Flow Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 21-activity-entity-data-flow-full

![21-activity-entity-data-flow-full](views/png/21-activity-entity-data-flow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/21-activity-entity-data-flow-full.mermaid`

## Описание
Views-диаграмма «Activity Entity Data Flow (Extract → Transform → Load)» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.8 (Transformation), §4.1 (ChEMBL Activity).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 21-activity-entity-data-flow-infra

![21-activity-entity-data-flow-infra](views/png/21-activity-entity-data-flow-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/21-activity-entity-data-flow-infra.mermaid`

## Описание
Views-диаграмма «21 Activity Entity Data Flow Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 21-activity-entity-data-flow-overview

![21-activity-entity-data-flow-overview](views/png/21-activity-entity-data-flow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/21-activity-entity-data-flow-overview.mermaid`

## Описание
Views-диаграмма «21 Activity Entity Data Flow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `21-activity-entity-data-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 26-hexagonal-ports-adapters-dataflow

![26-hexagonal-ports-adapters-dataflow](views/png/26-hexagonal-ports-adapters-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/26-hexagonal-ports-adapters-dataflow.mermaid`

## Описание
Views-диаграмма «26 Hexagonal Ports Adapters Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 26-hexagonal-ports-adapters-domain

![26-hexagonal-ports-adapters-domain](views/png/26-hexagonal-ports-adapters-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/26-hexagonal-ports-adapters-domain.mermaid`

## Описание
Views-диаграмма «26 Hexagonal Ports Adapters Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 26-hexagonal-ports-adapters-full

![26-hexagonal-ports-adapters-full](views/png/26-hexagonal-ports-adapters-full.png)

- Исходная диаграмма: `mmd-diagrams/views/26-hexagonal-ports-adapters-full.mermaid`

## Описание
Views-диаграмма «Hexagonal Architecture — Ports and Adapters Overview» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.2 (Ports & Adapters), §1.1 (Five-Layer Architecture).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 26-hexagonal-ports-adapters-infra

![26-hexagonal-ports-adapters-infra](views/png/26-hexagonal-ports-adapters-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/26-hexagonal-ports-adapters-infra.mermaid`

## Описание
Views-диаграмма «26 Hexagonal Ports Adapters Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 26-hexagonal-ports-adapters-overview

![26-hexagonal-ports-adapters-overview](views/png/26-hexagonal-ports-adapters-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/26-hexagonal-ports-adapters-overview.mermaid`

## Описание
Views-диаграмма «26 Hexagonal Ports Adapters Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `26-hexagonal-ports-adapters-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 28-composition-root-di-graph-dataflow

![28-composition-root-di-graph-dataflow](views/png/28-composition-root-di-graph-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/28-composition-root-di-graph-dataflow.mermaid`

## Описание
Views-диаграмма «28 Composition Root Di Graph Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 28-composition-root-di-graph-domain

![28-composition-root-di-graph-domain](views/png/28-composition-root-di-graph-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/28-composition-root-di-graph-domain.mermaid`

## Описание
Views-диаграмма «28 Composition Root Di Graph Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 28-composition-root-di-graph-full

![28-composition-root-di-graph-full](views/png/28-composition-root-di-graph-full.png)

- Исходная диаграмма: `mmd-diagrams/views/28-composition-root-di-graph-full.mermaid`

## Описание
Views-диаграмма «Composition Root Wiring — Full DI Graph» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Composition Layer), ADR-005.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 28-composition-root-di-graph-infra

![28-composition-root-di-graph-infra](views/png/28-composition-root-di-graph-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/28-composition-root-di-graph-infra.mermaid`

## Описание
Views-диаграмма «28 Composition Root Di Graph Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 28-composition-root-di-graph-overview

![28-composition-root-di-graph-overview](views/png/28-composition-root-di-graph-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/28-composition-root-di-graph-overview.mermaid`

## Описание
Views-диаграмма «28 Composition Root Di Graph Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `28-composition-root-di-graph-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 29-composite-pipeline-workflow-dataflow

![29-composite-pipeline-workflow-dataflow](views/png/29-composite-pipeline-workflow-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/29-composite-pipeline-workflow-dataflow.mermaid`

## Описание
Views-диаграмма «29 Composite Pipeline Workflow Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 29-composite-pipeline-workflow-domain

![29-composite-pipeline-workflow-domain](views/png/29-composite-pipeline-workflow-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/29-composite-pipeline-workflow-domain.mermaid`

## Описание
Views-диаграмма «29 Composite Pipeline Workflow Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 29-composite-pipeline-workflow-full

![29-composite-pipeline-workflow-full](views/png/29-composite-pipeline-workflow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/29-composite-pipeline-workflow-full.mermaid`

## Описание
Views-диаграмма «Composite Pipeline Full Workflow — Seed to Gold (ADR-026)» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.10 (Composite Pipelines), ADR-026.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 29-composite-pipeline-workflow-infra

![29-composite-pipeline-workflow-infra](views/png/29-composite-pipeline-workflow-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/29-composite-pipeline-workflow-infra.mermaid`

## Описание
Views-диаграмма «29 Composite Pipeline Workflow Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 29-composite-pipeline-workflow-overview

![29-composite-pipeline-workflow-overview](views/png/29-composite-pipeline-workflow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/29-composite-pipeline-workflow-overview.mermaid`

## Описание
Views-диаграмма «29 Composite Pipeline Workflow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `29-composite-pipeline-workflow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 30-port-adapter-mapping-dataflow

![30-port-adapter-mapping-dataflow](views/png/30-port-adapter-mapping-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/30-port-adapter-mapping-dataflow.mermaid`

## Описание
Views-диаграмма «30 Port Adapter Mapping Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 30-port-adapter-mapping-domain

![30-port-adapter-mapping-domain](views/png/30-port-adapter-mapping-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/30-port-adapter-mapping-domain.mermaid`

## Описание
Views-диаграмма «30 Port Adapter Mapping Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 30-port-adapter-mapping-full

![30-port-adapter-mapping-full](views/png/30-port-adapter-mapping-full.png)

- Исходная диаграмма: `mmd-diagrams/views/30-port-adapter-mapping-full.mermaid`

## Описание
Views-диаграмма «Port-to-Adapter Mapping Table Diagram» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.2 (Ports & Adapters), ARCH-008 (Single Source).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 30-port-adapter-mapping-infra

![30-port-adapter-mapping-infra](views/png/30-port-adapter-mapping-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/30-port-adapter-mapping-infra.mermaid`

## Описание
Views-диаграмма «30 Port Adapter Mapping Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 30-port-adapter-mapping-overview

![30-port-adapter-mapping-overview](views/png/30-port-adapter-mapping-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/30-port-adapter-mapping-overview.mermaid`

## Описание
Views-диаграмма «30 Port Adapter Mapping Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `30-port-adapter-mapping-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 31-pipeline-run-lifecycle-dataflow

![31-pipeline-run-lifecycle-dataflow](views/png/31-pipeline-run-lifecycle-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/31-pipeline-run-lifecycle-dataflow.mermaid`

## Описание
Views-диаграмма «31 Pipeline Run Lifecycle Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 31-pipeline-run-lifecycle-domain

![31-pipeline-run-lifecycle-domain](views/png/31-pipeline-run-lifecycle-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/31-pipeline-run-lifecycle-domain.mermaid`

## Описание
Views-диаграмма «31 Pipeline Run Lifecycle Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 31-pipeline-run-lifecycle-full

![31-pipeline-run-lifecycle-full](views/png/31-pipeline-run-lifecycle-full.png)

- Исходная диаграмма: `mmd-diagrams/views/31-pipeline-run-lifecycle-full.mermaid`

## Описание
Views-диаграмма «Pipeline Run Lifecycle — From Config to Completion» (уровень: Full) представлена в формате stateDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3 (Execution), domain/aggregates/pipeline_run.py.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 31-pipeline-run-lifecycle-infra

![31-pipeline-run-lifecycle-infra](views/png/31-pipeline-run-lifecycle-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/31-pipeline-run-lifecycle-infra.mermaid`

## Описание
Views-диаграмма «31 Pipeline Run Lifecycle Infra» (уровень: Infrastructure-Mapping) представлена в формате unknown. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`.

## Метаданные
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 31-pipeline-run-lifecycle-overview

![31-pipeline-run-lifecycle-overview](views/png/31-pipeline-run-lifecycle-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/31-pipeline-run-lifecycle-overview.mermaid`

## Описание
Views-диаграмма «31 Pipeline Run Lifecycle Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `31-pipeline-run-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 32-single-record-journey-dataflow

![32-single-record-journey-dataflow](views/png/32-single-record-journey-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/32-single-record-journey-dataflow.mermaid`

## Описание
Views-диаграмма «32 Single Record Journey Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `32-single-record-journey-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 32-single-record-journey-domain

![32-single-record-journey-domain](views/png/32-single-record-journey-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/32-single-record-journey-domain.mermaid`

## Описание
Views-диаграмма «32 Single Record Journey Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `32-single-record-journey-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 32-single-record-journey-full

![32-single-record-journey-full](views/png/32-single-record-journey-full.png)

- Исходная диаграмма: `mmd-diagrams/views/32-single-record-journey-full.mermaid`

## Описание
Views-диаграмма «Record Processing Pipeline — Single Record Journey» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.1-§2.6 (Data Flow, DQ), §2.8 (Normalization).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 32-single-record-journey-infra

![32-single-record-journey-infra](views/png/32-single-record-journey-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/32-single-record-journey-infra.mermaid`

## Описание
Views-диаграмма «32 Single Record Journey Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `32-single-record-journey-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 32-single-record-journey-overview

![32-single-record-journey-overview](views/png/32-single-record-journey-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/32-single-record-journey-overview.mermaid`

## Описание
Views-диаграмма «32 Single Record Journey Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `32-single-record-journey-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 33-cli-run-interaction-dataflow

![33-cli-run-interaction-dataflow](views/png/33-cli-run-interaction-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/33-cli-run-interaction-dataflow.mermaid`

## Описание
Views-диаграмма «33 Cli Run Interaction Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 33-cli-run-interaction-domain

![33-cli-run-interaction-domain](views/png/33-cli-run-interaction-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/33-cli-run-interaction-domain.mermaid`

## Описание
Views-диаграмма «33 Cli Run Interaction Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 33-cli-run-interaction-full

![33-cli-run-interaction-full](views/png/33-cli-run-interaction-full.png)

- Исходная диаграмма: `mmd-diagrams/views/33-cli-run-interaction-full.mermaid`

## Описание
Views-диаграмма «CLI Run Command → PipelineRunner Full Interaction» (уровень: Full) представлена в формате sequenceDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Interfaces → Composition → Application).

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 33-cli-run-interaction-infra

![33-cli-run-interaction-infra](views/png/33-cli-run-interaction-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/33-cli-run-interaction-infra.mermaid`

## Описание
Views-диаграмма «33 Cli Run Interaction Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 33-cli-run-interaction-overview

![33-cli-run-interaction-overview](views/png/33-cli-run-interaction-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/33-cli-run-interaction-overview.mermaid`

## Описание
Views-диаграмма «33 Cli Run Interaction Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `33-cli-run-interaction-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 34-batch-processing-flow-dataflow

![34-batch-processing-flow-dataflow](views/png/34-batch-processing-flow-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/34-batch-processing-flow-dataflow.mermaid`

## Описание
Views-диаграмма «34 Batch Processing Flow Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 34-batch-processing-flow-domain

![34-batch-processing-flow-domain](views/png/34-batch-processing-flow-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/34-batch-processing-flow-domain.mermaid`

## Описание
Views-диаграмма «34 Batch Processing Flow Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 34-batch-processing-flow-full

![34-batch-processing-flow-full](views/png/34-batch-processing-flow-full.png)

- Исходная диаграмма: `mmd-diagrams/views/34-batch-processing-flow-full.mermaid`

## Описание
Views-диаграмма «Batch Processing Flow — Extract to Write» (уровень: Full) представлена в формате sequenceDiagram. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.1 (Data Flow), application/core/batch_executor.py.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 34-batch-processing-flow-infra

![34-batch-processing-flow-infra](views/png/34-batch-processing-flow-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/34-batch-processing-flow-infra.mermaid`

## Описание
Views-диаграмма «34 Batch Processing Flow Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 34-batch-processing-flow-overview

![34-batch-processing-flow-overview](views/png/34-batch-processing-flow-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/34-batch-processing-flow-overview.mermaid`

## Описание
Views-диаграмма «34 Batch Processing Flow Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `34-batch-processing-flow-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 35-bootstrap-sequence-dataflow

![35-bootstrap-sequence-dataflow](views/png/35-bootstrap-sequence-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/35-bootstrap-sequence-dataflow.mermaid`

## Описание
Views-диаграмма «35 Bootstrap Sequence Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 35-bootstrap-sequence-domain

![35-bootstrap-sequence-domain](views/png/35-bootstrap-sequence-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/35-bootstrap-sequence-domain.mermaid`

## Описание
Views-диаграмма «35 Bootstrap Sequence Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 35-bootstrap-sequence-full

![35-bootstrap-sequence-full](views/png/35-bootstrap-sequence-full.png)

- Исходная диаграмма: `mmd-diagrams/views/35-bootstrap-sequence-full.mermaid`

## Описание
Views-диаграмма «Composition Layer Bootstrap Sequence» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1.1 (Composition Root), composition/bootstrap/runtime/.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 35-bootstrap-sequence-infra

![35-bootstrap-sequence-infra](views/png/35-bootstrap-sequence-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/35-bootstrap-sequence-infra.mermaid`

## Описание
Views-диаграмма «35 Bootstrap Sequence Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 35-bootstrap-sequence-overview

![35-bootstrap-sequence-overview](views/png/35-bootstrap-sequence-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/35-bootstrap-sequence-overview.mermaid`

## Описание
Views-диаграмма «35 Bootstrap Sequence Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `35-bootstrap-sequence-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 36-architecture-principles-mindmap-dataflow

![36-architecture-principles-mindmap-dataflow](views/png/36-architecture-principles-mindmap-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/36-architecture-principles-mindmap-dataflow.mermaid`

## Описание
Views-диаграмма «36 Architecture Principles Mindmap Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 36-architecture-principles-mindmap-domain

![36-architecture-principles-mindmap-domain](views/png/36-architecture-principles-mindmap-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/36-architecture-principles-mindmap-domain.mermaid`

## Описание
Views-диаграмма «36 Architecture Principles Mindmap Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 36-architecture-principles-mindmap-full

![36-architecture-principles-mindmap-full](views/png/36-architecture-principles-mindmap-full.png)

- Исходная диаграмма: `mmd-diagrams/views/36-architecture-principles-mindmap-full.mermaid`

## Описание
Views-диаграмма «Architecture Principles Mind Map» (уровень: Full) представлена в формате mindmap. Родительская диаграмма: `(root)`. Покрывает: RULES.md §1 (Architecture), all ADRs.

## Метаданные
- Тип: `mindmap`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 36-architecture-principles-mindmap-infra

![36-architecture-principles-mindmap-infra](views/png/36-architecture-principles-mindmap-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/36-architecture-principles-mindmap-infra.mermaid`

## Описание
Views-диаграмма «36 Architecture Principles Mindmap Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 36-architecture-principles-mindmap-overview

![36-architecture-principles-mindmap-overview](views/png/36-architecture-principles-mindmap-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/36-architecture-principles-mindmap-overview.mermaid`

## Описание
Views-диаграмма «36 Architecture Principles Mindmap Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `36-architecture-principles-mindmap-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 39-medallion-invariants-dataflow

![39-medallion-invariants-dataflow](views/png/39-medallion-invariants-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/39-medallion-invariants-dataflow.mermaid`

## Описание
Views-диаграмма «39 Medallion Invariants Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `39-medallion-invariants-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 39-medallion-invariants-domain

![39-medallion-invariants-domain](views/png/39-medallion-invariants-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/39-medallion-invariants-domain.mermaid`

## Описание
Views-диаграмма «39 Medallion Invariants Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `39-medallion-invariants-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 39-medallion-invariants-full

![39-medallion-invariants-full](views/png/39-medallion-invariants-full.png)

- Исходная диаграмма: `mmd-diagrams/views/39-medallion-invariants-full.mermaid`

## Описание
Views-диаграмма «Medallion Architecture Invariants (ARCH-007)» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §2.1 (Medallion), ARCH-007 clear policy.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 39-medallion-invariants-infra

![39-medallion-invariants-infra](views/png/39-medallion-invariants-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/39-medallion-invariants-infra.mermaid`

## Описание
Views-диаграмма «39 Medallion Invariants Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `39-medallion-invariants-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 39-medallion-invariants-overview

![39-medallion-invariants-overview](views/png/39-medallion-invariants-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/39-medallion-invariants-overview.mermaid`

## Описание
Views-диаграмма «39 Medallion Invariants Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `39-medallion-invariants-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 41-error-classification-tree-dataflow

![41-error-classification-tree-dataflow](views/png/41-error-classification-tree-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/41-error-classification-tree-dataflow.mermaid`

## Описание
Views-диаграмма «41 Error Classification Tree Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `41-error-classification-tree-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 41-error-classification-tree-domain

![41-error-classification-tree-domain](views/png/41-error-classification-tree-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/41-error-classification-tree-domain.mermaid`

## Описание
Views-диаграмма «41 Error Classification Tree Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `41-error-classification-tree-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 41-error-classification-tree-full

![41-error-classification-tree-full](views/png/41-error-classification-tree-full.png)

- Исходная диаграмма: `mmd-diagrams/views/41-error-classification-tree-full.mermaid`

## Описание
Views-диаграмма «Error Classification Decision Tree — Full Logic» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: RULES.md §3.1 (Error Handling), domain/exceptions/.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 41-error-classification-tree-infra

![41-error-classification-tree-infra](views/png/41-error-classification-tree-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/41-error-classification-tree-infra.mermaid`

## Описание
Views-диаграмма «41 Error Classification Tree Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `41-error-classification-tree-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 41-error-classification-tree-overview

![41-error-classification-tree-overview](views/png/41-error-classification-tree-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/41-error-classification-tree-overview.mermaid`

## Описание
Views-диаграмма «41 Error Classification Tree Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `41-error-classification-tree-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 44-cross-provider-enrichment-dataflow

![44-cross-provider-enrichment-dataflow](views/png/44-cross-provider-enrichment-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/44-cross-provider-enrichment-dataflow.mermaid`

## Описание
Views-диаграмма «44 Cross Provider Enrichment Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 44-cross-provider-enrichment-domain

![44-cross-provider-enrichment-domain](views/png/44-cross-provider-enrichment-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/44-cross-provider-enrichment-domain.mermaid`

## Описание
Views-диаграмма «44 Cross Provider Enrichment Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 44-cross-provider-enrichment-full

![44-cross-provider-enrichment-full](views/png/44-cross-provider-enrichment-full.png)

- Исходная диаграмма: `mmd-diagrams/views/44-cross-provider-enrichment-full.mermaid`

## Описание
Views-диаграмма «Cross-Provider Data Enrichment Flow — Publication» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: ADR-026 (Composite), publication composite pipeline config.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 44-cross-provider-enrichment-infra

![44-cross-provider-enrichment-infra](views/png/44-cross-provider-enrichment-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/44-cross-provider-enrichment-infra.mermaid`

## Описание
Views-диаграмма «44 Cross Provider Enrichment Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 44-cross-provider-enrichment-overview

![44-cross-provider-enrichment-overview](views/png/44-cross-provider-enrichment-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/44-cross-provider-enrichment-overview.mermaid`

## Описание
Views-диаграмма «44 Cross Provider Enrichment Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `44-cross-provider-enrichment-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 46-yaml-config-resolution-dataflow

![46-yaml-config-resolution-dataflow](views/png/46-yaml-config-resolution-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/46-yaml-config-resolution-dataflow.mermaid`

## Описание
Views-диаграмма «46 Yaml Config Resolution Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 46-yaml-config-resolution-domain

![46-yaml-config-resolution-domain](views/png/46-yaml-config-resolution-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/46-yaml-config-resolution-domain.mermaid`

## Описание
Views-диаграмма «46 Yaml Config Resolution Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 46-yaml-config-resolution-full

![46-yaml-config-resolution-full](views/png/46-yaml-config-resolution-full.png)

- Исходная диаграмма: `mmd-diagrams/views/46-yaml-config-resolution-full.mermaid`

## Описание
Views-диаграмма «YAML Configuration Resolution Chain» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: infrastructure/config_loader.py, infrastructure/config/, domain/config/.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 46-yaml-config-resolution-infra

![46-yaml-config-resolution-infra](views/png/46-yaml-config-resolution-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/46-yaml-config-resolution-infra.mermaid`

## Описание
Views-диаграмма «46 Yaml Config Resolution Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 46-yaml-config-resolution-overview

![46-yaml-config-resolution-overview](views/png/46-yaml-config-resolution-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/46-yaml-config-resolution-overview.mermaid`

## Описание
Views-диаграмма «46 Yaml Config Resolution Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `46-yaml-config-resolution-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 48-composite-phase-lifecycle-dataflow

![48-composite-phase-lifecycle-dataflow](views/png/48-composite-phase-lifecycle-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/48-composite-phase-lifecycle-dataflow.mermaid`

## Описание
Views-диаграмма «48 Composite Phase Lifecycle Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 48-composite-phase-lifecycle-domain

![48-composite-phase-lifecycle-domain](views/png/48-composite-phase-lifecycle-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/48-composite-phase-lifecycle-domain.mermaid`

## Описание
Views-диаграмма «48 Composite Phase Lifecycle Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 48-composite-phase-lifecycle-full

![48-composite-phase-lifecycle-full](views/png/48-composite-phase-lifecycle-full.png)

- Исходная диаграмма: `mmd-diagrams/views/48-composite-phase-lifecycle-full.mermaid`

## Описание
Views-диаграмма «Composite Pipeline Phase Lifecycle (FSM)» (уровень: Full) представлена в формате stateDiagram. Родительская диаграмма: `(root)`. Покрывает: domain/composite/state.py, application/composite/fsm_helper.py.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 48-composite-phase-lifecycle-infra

![48-composite-phase-lifecycle-infra](views/png/48-composite-phase-lifecycle-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/48-composite-phase-lifecycle-infra.mermaid`

## Описание
Views-диаграмма «48 Composite Phase Lifecycle Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 48-composite-phase-lifecycle-overview

![48-composite-phase-lifecycle-overview](views/png/48-composite-phase-lifecycle-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/48-composite-phase-lifecycle-overview.mermaid`

## Описание
Views-диаграмма «48 Composite Phase Lifecycle Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `48-composite-phase-lifecycle-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>

## 50-exception-hierarchy-dataflow

![50-exception-hierarchy-dataflow](views/png/50-exception-hierarchy-dataflow.png)

- Исходная диаграмма: `mmd-diagrams/views/50-exception-hierarchy-dataflow.mermaid`

## Описание
Views-диаграмма «50 Exception Hierarchy Dataflow» (уровень: Data-Flow) представлена в формате flowchart. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Data-Flow`

<div style="page-break-after: always;"></div>

## 50-exception-hierarchy-domain

![50-exception-hierarchy-domain](views/png/50-exception-hierarchy-domain.png)

- Исходная диаграмма: `mmd-diagrams/views/50-exception-hierarchy-domain.mermaid`

## Описание
Views-диаграмма «50 Exception Hierarchy Domain» (уровень: Domain-Focus) представлена в формате flowchart. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Domain-Focus`

<div style="page-break-after: always;"></div>

## 50-exception-hierarchy-full

![50-exception-hierarchy-full](views/png/50-exception-hierarchy-full.png)

- Исходная диаграмма: `mmd-diagrams/views/50-exception-hierarchy-full.mermaid`

## Описание
Views-диаграмма «Exception Hierarchy — Full Tree» (уровень: Full) представлена в формате flowchart. Родительская диаграмма: `(root)`. Покрывает: domain/exceptions/ (base, network, validation, internal, infrastructure, data_quality).

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
- Вид: `Full`

<div style="page-break-after: always;"></div>

## 50-exception-hierarchy-infra

![50-exception-hierarchy-infra](views/png/50-exception-hierarchy-infra.png)

- Исходная диаграмма: `mmd-diagrams/views/50-exception-hierarchy-infra.mermaid`

## Описание
Views-диаграмма «50 Exception Hierarchy Infra» (уровень: Infrastructure-Mapping) представлена в формате flowchart. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Infrastructure-Mapping`

<div style="page-break-after: always;"></div>

## 50-exception-hierarchy-overview

![50-exception-hierarchy-overview](views/png/50-exception-hierarchy-overview.png)

- Исходная диаграмма: `mmd-diagrams/views/50-exception-hierarchy-overview.mermaid`

## Описание
Views-диаграмма «50 Exception Hierarchy Overview» (уровень: Overview) представлена в формате flowchart. Родительская диаграмма: `50-exception-hierarchy-full.mermaid`.

## Метаданные
- Тип: `flowchart`
- Вид: `Overview`

<div style="page-break-after: always;"></div>
