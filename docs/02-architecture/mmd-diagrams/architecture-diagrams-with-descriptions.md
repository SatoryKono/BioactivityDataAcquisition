# BioETL Architecture Diagrams With Descriptions

- Generated: 2026-03-12T13:00:59
- Diagram count: 52

## Table of Contents

- [01-high-level-hexagonal](#01-high-level-hexagonal)
- [01a-hexagonal-overview](#01a-hexagonal-overview)
- [01b-hexagonal-domain-app](#01b-hexagonal-domain-app)
- [01c-hexagonal-infra-comp](#01c-hexagonal-infra-comp)
- [01d-hexagonal-overview-rounded](#01d-hexagonal-overview-rounded)
- [02-layer-dependency-matrix](#02-layer-dependency-matrix)
- [03-medallion-data-flow](#03-medallion-data-flow)
- [03a-medallion-layers-overview](#03a-medallion-layers-overview)
- [04-pipeline-execution-flow](#04-pipeline-execution-flow)
- [05-provider-adapter-hierarchy](#05-provider-adapter-hierarchy)
- [05a-adapter-hierarchy-base](#05a-adapter-hierarchy-base)
- [05b-adapter-hierarchy-providers](#05b-adapter-hierarchy-providers)
- [06-storage-layer](#06-storage-layer)
- [06a-storage-writers](#06a-storage-writers)
- [06b-storage-support](#06b-storage-support)
- [07-dq-system](#07-dq-system)
- [07a-dq-analysis](#07a-dq-analysis)
- [07b-dq-pipeline](#07b-dq-pipeline)
- [08-composite-pipeline](#08-composite-pipeline)
- [08a-composite-config](#08a-composite-config)
- [08b-composite-execution](#08b-composite-execution)
- [09-observability-stack](#09-observability-stack)
- [09a-observability-app](#09a-observability-app)
- [09b-observability-infra](#09b-observability-infra)
- [10-resilience-patterns](#10-resilience-patterns)
- [11-configuration-system](#11-configuration-system)
- [11a-config-loading](#11a-config-loading)
- [11b-config-domain](#11b-config-domain)
- [12-bootstrap-di-container](#12-bootstrap-di-container)
- [12a-bootstrap-factories](#12a-bootstrap-factories)
- [12b-bootstrap-wiring](#12b-bootstrap-wiring)
- [13-port-protocol-contracts](#13-port-protocol-contracts)
- [13a-data-storage-ports](#13a-data-storage-ports)
- [13a-port-contracts-data-sources](#13a-port-contracts-data-sources)
- [13b-operational-ports](#13b-operational-ports)
- [13b-port-contracts-storage](#13b-port-contracts-storage)
- [13c-port-contracts-observability](#13c-port-contracts-observability)
- [13c-validation-dq-ports](#13c-validation-dq-ports)
- [13d-port-contracts-services](#13d-port-contracts-services)
- [13e-operational-ports-domain](#13e-operational-ports-domain)
- [13f-operational-ports-infra](#13f-operational-ports-infra)
- [14-cli-interface-layer](#14-cli-interface-layer)
- [14a-cli-commands](#14a-cli-commands)
- [14b-cli-routing](#14b-cli-routing)
- [15-batch-executor-internals](#15-batch-executor-internals)
- [16-transformer-hierarchy](#16-transformer-hierarchy)
- [16a-transformer-base](#16a-transformer-base)
- [16b-transformer-pub-other](#16b-transformer-pub-other)
- [17-security-pii-audit](#17-security-pii-audit)
- [18-lock-checkpoint-shutdown](#18-lock-checkpoint-shutdown)
- [18a-lock-system](#18a-lock-system)
- [18b-checkpoint-shutdown](#18b-checkpoint-shutdown)

---

## 01-high-level-hexagonal

![01-high-level-hexagonal](architecture/png/01-high-level-hexagonal.png)

- Исходная диаграмма: `mmd-diagrams/architecture/01-high-level-hexagonal.mmd`

## Описание
Архитектурная диаграмма «High-Level Hexagonal Architecture» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: the Ports & Adapters (Hexagonal) pattern across all layers.. Количество узлов: 46. Примечание: Decomposed into 01a, 01b, 01c sub-diagrams.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `46`

<div style="page-break-after: always;"></div>

## 01a-hexagonal-overview

![01a-hexagonal-overview](architecture/png/01a-hexagonal-overview.png)

- Исходная диаграмма: `mmd-diagrams/architecture/01a-hexagonal-overview.mmd`

## Описание
Архитектурная диаграмма «Hexagonal Overview» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 11.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `11`

<div style="page-break-after: always;"></div>

## 01b-hexagonal-domain-app

![01b-hexagonal-domain-app](architecture/png/01b-hexagonal-domain-app.png)

- Исходная диаграмма: `mmd-diagrams/architecture/01b-hexagonal-domain-app.mmd`

## Описание
Архитектурная диаграмма «Hexagonal Domain and Application» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 13.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `13`

<div style="page-break-after: always;"></div>

## 01c-hexagonal-infra-comp

![01c-hexagonal-infra-comp](architecture/png/01c-hexagonal-infra-comp.png)

- Исходная диаграмма: `mmd-diagrams/architecture/01c-hexagonal-infra-comp.mmd`

## Описание
Архитектурная диаграмма «Hexagonal Infrastructure and Composition» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 14.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `14`

<div style="page-break-after: always;"></div>

## 01d-hexagonal-overview-rounded

![01d-hexagonal-overview-rounded](architecture/png/01d-hexagonal-overview-rounded.png)

- Исходная диаграмма: `mmd-diagrams/architecture/01d-hexagonal-overview-rounded.mmd`

## Описание
Архитектурная диаграмма «Hexagonal Overview (Rounded Nodes)» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 11.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-01`
- Узлы: `11`

<div style="page-break-after: always;"></div>

## 02-layer-dependency-matrix

![02-layer-dependency-matrix](architecture/png/02-layer-dependency-matrix.png)

- Исходная диаграмма: `mmd-diagrams/architecture/02-layer-dependency-matrix.mmd`

## Описание
Архитектурная диаграмма «Layer Dependency Matrix (ARCH-001)» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 5.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `5`

<div style="page-break-after: always;"></div>

## 03-medallion-data-flow

![03-medallion-data-flow](architecture/png/03-medallion-data-flow.png)

- Исходная диаграмма: `mmd-diagrams/architecture/03-medallion-data-flow.mmd`

## Описание
Архитектурная диаграмма «Medallion Architecture Data Flow (Bronze → Silver → Gold)» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: how data flows through the three medallion layers.. Количество узлов: 36. Примечание: Canonical medallion flow — at threshold boundary.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `36`

<div style="page-break-after: always;"></div>

## 03a-medallion-layers-overview

![03a-medallion-layers-overview](architecture/png/03a-medallion-layers-overview.png)

- Исходная диаграмма: `mmd-diagrams/architecture/03a-medallion-layers-overview.mmd`

## Описание
Архитектурная диаграмма «Medallion Layers Overview» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 04-pipeline-execution-flow

![04-pipeline-execution-flow](architecture/png/04-pipeline-execution-flow.png)

- Исходная диаграмма: `mmd-diagrams/architecture/04-pipeline-execution-flow.mmd`

## Описание
Архитектурная диаграмма «Pipeline Execution Lifecycle» из набора architecture представлена в формате sequenceDiagram. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 05-provider-adapter-hierarchy

![05-provider-adapter-hierarchy](architecture/png/05-provider-adapter-hierarchy.png)

- Исходная диаграмма: `mmd-diagrams/architecture/05-provider-adapter-hierarchy.mmd`

## Описание
Архитектурная диаграмма «Provider Adapter Hierarchy» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: how each provider adapter inherits from base classes and implements DataSourcePort.. Количество узлов: 27. Примечание: Decomposed into 05a, 05b sub-diagrams.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `27`

<div style="page-break-after: always;"></div>

## 05a-adapter-hierarchy-base

![05a-adapter-hierarchy-base](architecture/png/05a-adapter-hierarchy-base.png)

- Исходная диаграмма: `mmd-diagrams/architecture/05a-adapter-hierarchy-base.mmd`

## Описание
Архитектурная диаграмма «Adapter Hierarchy: Base Types» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 05b-adapter-hierarchy-providers

![05b-adapter-hierarchy-providers](architecture/png/05b-adapter-hierarchy-providers.png)

- Исходная диаграмма: `mmd-diagrams/architecture/05b-adapter-hierarchy-providers.mmd`

## Описание
Архитектурная диаграмма «Adapter Hierarchy: Provider Implementations» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 15.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `15`

<div style="page-break-after: always;"></div>

## 06-storage-layer

![06-storage-layer](architecture/png/06-storage-layer.png)

- Исходная диаграмма: `mmd-diagrams/architecture/06-storage-layer.mmd`

## Описание
Архитектурная диаграмма «Storage Layer Components» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: Bronze/Silver/Gold writers, Delta Lake, metadata, and validation.. Количество узлов: 21. Примечание: Decomposed into 06a-storage-writers, 06b-storage-support.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `21`

<div style="page-break-after: always;"></div>

## 06a-storage-writers

![06a-storage-writers](architecture/png/06a-storage-writers.png)

- Исходная диаграмма: `mmd-diagrams/architecture/06a-storage-writers.mmd`

## Описание
Архитектурная диаграмма «Storage Writers» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 10.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `10`

<div style="page-break-after: always;"></div>

## 06b-storage-support

![06b-storage-support](architecture/png/06b-storage-support.png)

- Исходная диаграмма: `mmd-diagrams/architecture/06b-storage-support.mmd`

## Описание
Архитектурная диаграмма «Storage Support Components» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 11.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `11`

<div style="page-break-after: always;"></div>

## 07-dq-system

![07-dq-system](architecture/png/07-dq-system.png)

- Исходная диаграмма: `mmd-diagrams/architecture/07-dq-system.mmd`

## Описание
Архитектурная диаграмма «Data Quality (DQ) System» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: DQ monitoring, analysis, and reporting across all medallion layers.. Количество узлов: 22. Примечание: Decomposed into 07a-dq-analysis, 07b-dq-pipeline.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `22`

<div style="page-break-after: always;"></div>

## 07a-dq-analysis

![07a-dq-analysis](architecture/png/07a-dq-analysis.png)

- Исходная диаграмма: `mmd-diagrams/architecture/07a-dq-analysis.mmd`

## Описание
Архитектурная диаграмма «DQ Analysis Services» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 07b-dq-pipeline

![07b-dq-pipeline](architecture/png/07b-dq-pipeline.png)

- Исходная диаграмма: `mmd-diagrams/architecture/07b-dq-pipeline.mmd`

## Описание
Архитектурная диаграмма «DQ Pipeline Integration» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 10.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `10`

<div style="page-break-after: always;"></div>

## 08-composite-pipeline

![08-composite-pipeline](architecture/png/08-composite-pipeline.png)

- Исходная диаграмма: `mmd-diagrams/architecture/08-composite-pipeline.mmd`

## Описание
Архитектурная диаграмма «Composite Pipeline Architecture» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: seed → dependencies → enrichers (parallel) → merge flow.. Количество узлов: 33. Примечание: Decomposed into 08a-composite-config, 08b-composite-execution.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `33`

<div style="page-break-after: always;"></div>

## 08a-composite-config

![08a-composite-config](architecture/png/08a-composite-config.png)

- Исходная диаграмма: `mmd-diagrams/architecture/08a-composite-config.mmd`

## Описание
Архитектурная диаграмма «Composite Pipeline Configuration & FSM» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 13.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `13`

<div style="page-break-after: always;"></div>

## 08b-composite-execution

![08b-composite-execution](architecture/png/08b-composite-execution.png)

- Исходная диаграмма: `mmd-diagrams/architecture/08b-composite-execution.mmd`

## Описание
Архитектурная диаграмма «Composite Pipeline Execution» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 20.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `20`

<div style="page-break-after: always;"></div>

## 09-observability-stack

![09-observability-stack](architecture/png/09-observability-stack.png)

- Исходная диаграмма: `mmd-diagrams/architecture/09-observability-stack.mmd`

## Описание
Архитектурная диаграмма «Observability Stack» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 24. Примечание: Decomposed into 09a-observability-app, 09b-observability-infra.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `24`

<div style="page-break-after: always;"></div>

## 09a-observability-app

![09a-observability-app](architecture/png/09a-observability-app.png)

- Исходная диаграмма: `mmd-diagrams/architecture/09a-observability-app.mmd`

## Описание
Архитектурная диаграмма «Observability: Application Layer» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 8.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `8`

<div style="page-break-after: always;"></div>

## 09b-observability-infra

![09b-observability-infra](architecture/png/09b-observability-infra.png)

- Исходная диаграмма: `mmd-diagrams/architecture/09b-observability-infra.mmd`

## Описание
Архитектурная диаграмма «Observability: Infrastructure Layer» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 13.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `13`

<div style="page-break-after: always;"></div>

## 10-resilience-patterns

![10-resilience-patterns](architecture/png/10-resilience-patterns.png)

- Исходная диаграмма: `mmd-diagrams/architecture/10-resilience-patterns.mmd`

## Описание
Архитектурная диаграмма «Resilience Patterns» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 15.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `15`

<div style="page-break-after: always;"></div>

## 11-configuration-system

![11-configuration-system](architecture/png/11-configuration-system.png)

- Исходная диаграмма: `mmd-diagrams/architecture/11-configuration-system.mmd`

## Описание
Архитектурная диаграмма «Configuration System» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: how YAML configs are loaded, validated, and used across the system.. Количество узлов: 29. Примечание: Decomposed into 11a-config-loading, 11b-config-domain.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `29`

<div style="page-break-after: always;"></div>

## 11a-config-loading

![11a-config-loading](architecture/png/11a-config-loading.png)

- Исходная диаграмма: `mmd-diagrams/architecture/11a-config-loading.mmd`

## Описание
Архитектурная диаграмма «Configuration: Loading Pipeline» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 13.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `13`

<div style="page-break-after: always;"></div>

## 11b-config-domain

![11b-config-domain](architecture/png/11b-config-domain.png)

- Исходная диаграмма: `mmd-diagrams/architecture/11b-config-domain.mmd`

## Описание
Архитектурная диаграмма «Configuration: Domain & Application Config» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 16.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `16`

<div style="page-break-after: always;"></div>

## 12-bootstrap-di-container

![12-bootstrap-di-container](architecture/png/12-bootstrap-di-container.png)

- Исходная диаграмма: `mmd-diagrams/architecture/12-bootstrap-di-container.mmd`

## Описание
Архитектурная диаграмма «Bootstrap / DI Container (Composition Root)» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: how dependencies are assembled and wired together.. Количество узлов: 29. Примечание: Decomposed into 12a, 12b sub-diagrams.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `29`

<div style="page-break-after: always;"></div>

## 12a-bootstrap-factories

![12a-bootstrap-factories](architecture/png/12a-bootstrap-factories.png)

- Исходная диаграмма: `mmd-diagrams/architecture/12a-bootstrap-factories.mmd`

## Описание
Архитектурная диаграмма «Bootstrap: Factories and Registries» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 10.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `10`

<div style="page-break-after: always;"></div>

## 12b-bootstrap-wiring

![12b-bootstrap-wiring](architecture/png/12b-bootstrap-wiring.png)

- Исходная диаграмма: `mmd-diagrams/architecture/12b-bootstrap-wiring.mmd`

## Описание
Архитектурная диаграмма «Bootstrap: Wiring Graph» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 15.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `15`

<div style="page-break-after: always;"></div>

## 13-port-protocol-contracts

![13-port-protocol-contracts](architecture/png/13-port-protocol-contracts.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13-port-protocol-contracts.mmd`

## Описание
Архитектурная диаграмма «Port/Protocol Contracts (Full Map)» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 68. Примечание: Decomposed into 13a, 13b, 13c, 13d sub-diagrams.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `68`

<div style="page-break-after: always;"></div>

## 13a-data-storage-ports

![13a-data-storage-ports](architecture/png/13a-data-storage-ports.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13a-data-storage-ports.mmd`

## Описание
Архитектурная диаграмма «DataSource and Storage Ports» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 20.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `20`

<div style="page-break-after: always;"></div>

## 13a-port-contracts-data-sources

![13a-port-contracts-data-sources](architecture/png/13a-port-contracts-data-sources.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13a-port-contracts-data-sources.mmd`

## Описание
Архитектурная диаграмма «Port Contracts: Data Sources» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 9.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `9`

<div style="page-break-after: always;"></div>

## 13b-operational-ports

![13b-operational-ports](architecture/png/13b-operational-ports.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13b-operational-ports.mmd`

## Описание
Архитектурная диаграмма «Operational and Observability Ports» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 25. Примечание: Decomposed into 13e-operational-ports-domain, 13f-operational-ports-infra.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `25`

<div style="page-break-after: always;"></div>

## 13b-port-contracts-storage

![13b-port-contracts-storage](architecture/png/13b-port-contracts-storage.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13b-port-contracts-storage.mmd`

## Описание
Архитектурная диаграмма «Port Contracts: Storage» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 9.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `9`

<div style="page-break-after: always;"></div>

## 13c-port-contracts-observability

![13c-port-contracts-observability](architecture/png/13c-port-contracts-observability.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13c-port-contracts-observability.mmd`

## Описание
Архитектурная диаграмма «Port Contracts: Observability and Resilience» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 15.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `15`

<div style="page-break-after: always;"></div>

## 13c-validation-dq-ports

![13c-validation-dq-ports](architecture/png/13c-validation-dq-ports.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13c-validation-dq-ports.mmd`

## Описание
Архитектурная диаграмма «Validation and Data Quality Ports» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 20.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `20`

<div style="page-break-after: always;"></div>

## 13d-port-contracts-services

![13d-port-contracts-services](architecture/png/13d-port-contracts-services.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13d-port-contracts-services.mmd`

## Описание
Архитектурная диаграмма «Port Contracts: Services and Controls» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 20.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
- Узлы: `20`

<div style="page-break-after: always;"></div>

## 13e-operational-ports-domain

![13e-operational-ports-domain](architecture/png/13e-operational-ports-domain.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13e-operational-ports-domain.mmd`

## Описание
Архитектурная диаграмма «Domain Operational Ports» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 8.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `8`

<div style="page-break-after: always;"></div>

## 13f-operational-ports-infra

![13f-operational-ports-infra](architecture/png/13f-operational-ports-infra.png)

- Исходная диаграмма: `mmd-diagrams/architecture/13f-operational-ports-infra.mmd`

## Описание
Архитектурная диаграмма «Infrastructure Operational Implementations» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 7.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `7`

<div style="page-break-after: always;"></div>

## 14-cli-interface-layer

![14-cli-interface-layer](architecture/png/14-cli-interface-layer.png)

- Исходная диаграмма: `mmd-diagrams/architecture/14-cli-interface-layer.mmd`

## Описание
Архитектурная диаграмма «CLI / Interface Layer» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: CLI commands, their routing, and interaction with composition.. Количество узлов: 24. Примечание: Decomposed into 14a-cli-commands, 14b-cli-routing.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `24`

<div style="page-break-after: always;"></div>

## 14a-cli-commands

![14a-cli-commands](architecture/png/14a-cli-commands.png)

- Исходная диаграмма: `mmd-diagrams/architecture/14a-cli-commands.mmd`

## Описание
Архитектурная диаграмма «CLI: Command Structure» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 14b-cli-routing

![14b-cli-routing](architecture/png/14b-cli-routing.png)

- Исходная диаграмма: `mmd-diagrams/architecture/14b-cli-routing.mmd`

## Описание
Архитектурная диаграмма «CLI: Routing to Composition & Application» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 12.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `12`

<div style="page-break-after: always;"></div>

## 15-batch-executor-internals

![15-batch-executor-internals](architecture/png/15-batch-executor-internals.png)

- Исходная диаграмма: `mmd-diagrams/architecture/15-batch-executor-internals.mmd`

## Описание
Архитектурная диаграмма «BatchExecutor Internal Architecture» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: the composition of BatchExecutor and its helper components.. Количество узлов: 15.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `15`

<div style="page-break-after: always;"></div>

## 16-transformer-hierarchy

![16-transformer-hierarchy](architecture/png/16-transformer-hierarchy.png)

- Исходная диаграмма: `mmd-diagrams/architecture/16-transformer-hierarchy.mmd`

## Описание
Архитектурная диаграмма «Transformer Hierarchy» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: the Template Method pattern and all provider-specific transformers.. Количество узлов: 35. Примечание: Decomposed into 16a-transformer-base, 16b-transformer-pub-other.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `35`

<div style="page-break-after: always;"></div>

## 16a-transformer-base

![16a-transformer-base](architecture/png/16a-transformer-base.png)

- Исходная диаграмма: `mmd-diagrams/architecture/16a-transformer-base.mmd`

## Описание
Архитектурная диаграмма «Base Transformer and ChEMBL Transformers» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 17.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `17`

<div style="page-break-after: always;"></div>

## 16b-transformer-pub-other

![16b-transformer-pub-other](architecture/png/16b-transformer-pub-other.png)

- Исходная диаграмма: `mmd-diagrams/architecture/16b-transformer-pub-other.mmd`

## Описание
Архитектурная диаграмма «Publication, UniProt, Other Transformers and Extractors» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 18.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `18`

<div style="page-break-after: always;"></div>

## 17-security-pii-audit

![17-security-pii-audit](architecture/png/17-security-pii-audit.png)

- Исходная диаграмма: `mmd-diagrams/architecture/17-security-pii-audit.mmd`

## Описание
Архитектурная диаграмма «Security, PII Hashing, and Audit Trail» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: how PII is handled and audit trail is maintained.. Количество узлов: 16.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `16`

<div style="page-break-after: always;"></div>

## 18-lock-checkpoint-shutdown

![18-lock-checkpoint-shutdown](architecture/png/18-lock-checkpoint-shutdown.png)

- Исходная диаграмма: `mmd-diagrams/architecture/18-lock-checkpoint-shutdown.mmd`

## Описание
Архитектурная диаграмма «Locking, Checkpoint, and Graceful Shutdown» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Показывает: distributed safety mechanisms.. Количество узлов: 22. Примечание: Decomposed into 18a-lock-system, 18b-checkpoint-shutdown.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
- Узлы: `22`

<div style="page-break-after: always;"></div>

## 18a-lock-system

![18a-lock-system](architecture/png/18a-lock-system.png)

- Исходная диаграмма: `mmd-diagrams/architecture/18a-lock-system.mmd`

## Описание
Архитектурная диаграмма «Lock System» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 8.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `8`

<div style="page-break-after: always;"></div>

## 18b-checkpoint-shutdown

![18b-checkpoint-shutdown](architecture/png/18b-checkpoint-shutdown.png)

- Исходная диаграмма: `mmd-diagrams/architecture/18b-checkpoint-shutdown.mmd`

## Описание
Архитектурная диаграмма «Checkpoint and Shutdown System» из набора architecture представлена в формате flowchart. Уровень детализации: System / Component. Количество узлов: 14.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
- Узлы: `14`

<div style="page-break-after: always;"></div>
