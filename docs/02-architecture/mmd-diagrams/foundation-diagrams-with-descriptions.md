# BioETL Foundation Diagrams With Descriptions

- Generated: 2026-03-03
- Diagram count: 54

## Table of Contents

- [01-full-system-component](#01-full-system-component)
- [01-high-level](#01-high-level)
- [02-full-medallion-data-flow](#02-full-medallion-data-flow)
- [03-pipeline-execution-happy-path](#03-pipeline-execution-happy-path)
- [04-domain-layer-class-diagram](#04-domain-layer-class-diagram)
- [04-error-flow](#04-error-flow)
- [05-layers-interaction](#05-layers-interaction)
- [05-pipeline-lifecycle-states](#05-pipeline-lifecycle-states)
- [06-application-layer-class-diagram](#06-application-layer-class-diagram)
- [06-pipeline-execution](#06-pipeline-execution)
- [07-circuit-breaker-states](#07-circuit-breaker-states)
- [07-medallion-flow](#07-medallion-flow)
- [08-complete-etl-workflow](#08-complete-etl-workflow)
- [08-domain-ddd](#08-domain-ddd)
- [09-full-er-diagram](#09-full-er-diagram)
- [10-infrastructure-layer-class-diagram](#10-infrastructure-layer-class-diagram)
- [11-lock-acquisition-sequence](#11-lock-acquisition-sequence)
- [12-local-deployment-architecture](#12-local-deployment-architecture)
- [13-domain-models-relationship](#13-domain-models-relationship)
- [14-provider-health-states](#14-provider-health-states)
- [15-dq-check-workflow](#15-dq-check-workflow)
- [16-memory-lock-class](#16-memory-lock-class)
- [17-pipeline-hierarchy](#17-pipeline-hierarchy)
- [18-bronze-write-sequence](#18-bronze-write-sequence)
- [19-delta-lake-write-sequence](#19-delta-lake-write-sequence)
- [20-quarantine-record-states](#20-quarantine-record-states)
- [21-activity-entity-data-flow](#21-activity-entity-data-flow)
- [22-client-api-request-sequence](#22-client-api-request-sequence)
- [23-silver-writer-class](#23-silver-writer-class)
- [24-hash-service-class](#24-hash-service-class)
- [25-circuit-breaker-observer-class](#25-circuit-breaker-observer-class)
- [26-hexagonal-ports-adapters](#26-hexagonal-ports-adapters)
- [27-import-matrix-enforcement](#27-import-matrix-enforcement)
- [28-composition-root-di-graph](#28-composition-root-di-graph)
- [29-composite-pipeline-workflow](#29-composite-pipeline-workflow)
- [30-port-adapter-mapping](#30-port-adapter-mapping)
- [31-pipeline-run-lifecycle](#31-pipeline-run-lifecycle)
- [32-single-record-journey](#32-single-record-journey)
- [33-cli-run-interaction](#33-cli-run-interaction)
- [34-batch-processing-flow](#34-batch-processing-flow)
- [36-architecture-principles-mindmap](#36-architecture-principles-mindmap)
- [37-cli-entry-full-chain](#37-cli-entry-full-chain)
- [38-runtime-assembly-sequence](#38-runtime-assembly-sequence)
- [39-medallion-invariants](#39-medallion-invariants)
- [40-application-core-collaboration](#40-application-core-collaboration)
- [41-error-classification-tree](#41-error-classification-tree)
- [42-pipeline-runner-class](#42-pipeline-runner-class)
- [43-fan-out-fan-in-pattern](#43-fan-out-fan-in-pattern)
- [44-cross-provider-enrichment](#44-cross-provider-enrichment)
- [46-yaml-config-resolution](#46-yaml-config-resolution)
- [47-publication-merge-sources](#47-publication-merge-sources)
- [48-composite-phase-lifecycle](#48-composite-phase-lifecycle)
- [49-composite-runner-class](#49-composite-runner-class)
- [50-exception-hierarchy](#50-exception-hierarchy)

---

## 01-full-system-component

![01-full-system-component](foundation/png/01-full-system-component.png)

- Исходная диаграмма: `mmd-diagrams/foundation/01-full-system-component.mmd`

## Описание
Диаграмма Title: Full System Component Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 01-full-system-component. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Five-Layer Architecture), §1.2 (Ports & Adapters). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External Systems, Bioactivity Sources, Publication Sources, Interfaces Layer, Composition Layer. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External Systems, Bioactivity Sources, ChEMBL API, PubChem API, UniProt API, Publication Sources. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`

<div style="page-break-after: always;"></div>

---

## 01-high-level

![01-high-level](foundation/png/01-high-level.png)

- Исходная диаграмма: `mmd-diagrams/foundation/01-high-level.mmd`

## Описание
Диаграмма Title: High-Level System Architecture из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 01-high-level. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Five-Layer Architecture). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External Data Sources, Interfaces Layer, Composition Layer, Application Layer, Infrastructure Layer. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External Data Sources, ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 02-full-medallion-data-flow

![02-full-medallion-data-flow](foundation/png/02-full-medallion-data-flow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/02-full-medallion-data-flow.mmd`

## Описание
Диаграмма Title: Full Medallion Data Flow with Lineage and DQ из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 02-full-medallion-data-flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Medallion Architecture), §2.3 (Quarantine), §3.1 (DQ). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External Sources, Bronze Layer, Silver Layer, Gold Layer, Data Quality Branch. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External Sources, ChEMBL API, PubChem API, UniProt API, PubMed API, CrossRef API. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 03-pipeline-execution-happy-path

![03-pipeline-execution-happy-path](foundation/png/03-pipeline-execution-happy-path.png)

- Исходная диаграмма: `mmd-diagrams/foundation/03-pipeline-execution-happy-path.mmd`

## Описание
Диаграмма Title: Pipeline Execution — Happy Path из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 03-pipeline-execution-happy-path. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Pipeline Execution), §3.3 (Locking), §3.4 (Postrun). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: CLI, bootstrap_pipeline(), PipelineRunner, LockCoordinator, PreflightService. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 04-domain-layer-class-diagram

![04-domain-layer-class-diagram](foundation/png/04-domain-layer-class-diagram.png)

- Исходная диаграмма: `mmd-diagrams/foundation/04-domain-layer-class-diagram.mmd`

## Описание
Диаграмма Title: Domain Layer Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 04-domain-layer-class-diagram. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Domain Layer), §1.2 (Ports), §1.3 (Entities). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 04-error-flow

![04-error-flow](foundation/png/04-error-flow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/04-error-flow.mmd`

## Описание
Диаграмма Title: Error Handling and Quarantine Flow из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 04-error-flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.1 (Error Classification), §2.3 (Quarantine). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Pipeline Execution, Error Classification (§3.1), Error Handling, Quarantine (§2.3). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Pipeline Execution, Error Classification (§3.1), Error Handling, Quarantine (§2.3). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 05-layers-interaction

![05-layers-interaction](foundation/png/05-layers-interaction.png)

- Исходная диаграмма: `mmd-diagrams/foundation/05-layers-interaction.mmd`

## Описание
Диаграмма Title: Layer Interaction — Hexagonal Architecture из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 05-layers-interaction. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Layers), §1.2 (Ports & Adapters). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Interfaces Layer, Composition Layer, Application Layer, Composite Pipeline (ADR-026), Domain Layer. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Interfaces Layer, Composition Layer, Application Layer, Composite Pipeline (ADR-026), Domain Layer, Infrastructure Layer. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 05-pipeline-lifecycle-states

![05-pipeline-lifecycle-states](foundation/png/05-pipeline-lifecycle-states.png)

- Исходная диаграмма: `mmd-diagrams/foundation/05-pipeline-lifecycle-states.mmd`

## Описание
Диаграмма Title: Pipeline Lifecycle State Machine из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 05-pipeline-lifecycle-states. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Pipeline Execution), §3.5 (Graceful Shutdown). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 06-application-layer-class-diagram

![06-application-layer-class-diagram](foundation/png/06-application-layer-class-diagram.png)

- Исходная диаграмма: `mmd-diagrams/foundation/06-application-layer-class-diagram.mmd`

## Описание
Диаграмма Title: Application Layer Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 06-application-layer-class-diagram. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Application Layer), §3 (Pipeline Execution). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 06-pipeline-execution

![06-pipeline-execution](foundation/png/06-pipeline-execution.png)

- Исходная диаграмма: `mmd-diagrams/foundation/06-pipeline-execution.mmd`

## Описание
Диаграмма Title: Pipeline Execution Sequence (Full) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 06-pipeline-execution. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Pipeline Execution), §3.2 (Preflight), §3.4 (Postrun). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: CLI, bootstrap_pipeline, PipelineRunner, PreflightService, PipelineExecutor. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 07-circuit-breaker-states

![07-circuit-breaker-states](foundation/png/07-circuit-breaker-states.png)

- Исходная диаграмма: `mmd-diagrams/foundation/07-circuit-breaker-states.mmd`

## Описание
Диаграмма Title: Circuit Breaker State Machine из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 07-circuit-breaker-states. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.6 (Resilience), ADR-007. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 07-medallion-flow

![07-medallion-flow](foundation/png/07-medallion-flow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/07-medallion-flow.mmd`

## Описание
Диаграмма Title: Medallion Data Flow (Sources → Bronze → Silver → Gold) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 07-medallion-flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Medallion Architecture), §2.8 (Transformation). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External Sources, Bronze Layer, Silver Layer, Gold Layer, Data Characteristics. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External Sources, Bronze Layer, JSONL + zstd Append-only 90d retention, Silver Layer, Delta Lake Merge/Upsert ACID transactions, Gold Layer. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 08-complete-etl-workflow

![08-complete-etl-workflow](foundation/png/08-complete-etl-workflow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/08-complete-etl-workflow.mmd`

## Описание
Диаграмма Title: Complete ETL Workflow (6 Phases) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 08-complete-etl-workflow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Pipeline Execution), §3.2 (Preflight), §3.4 (Postrun). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Phase 1: Prepare, Phase 2: Extract, Phase 3: Transform, Normalization Rules, Metadata Fields. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Phase 1: Prepare, Phase 2: Extract, Phase 3: Transform, Normalization Rules, NaN/Inf → null, Floats → round(10). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 08-domain-ddd

![08-domain-ddd](foundation/png/08-domain-ddd.png)

- Исходная диаграмма: `mmd-diagrams/foundation/08-domain-ddd.mmd`

## Описание
Диаграмма Title: Domain Layer — DDD Components из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 08-domain-ddd. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Domain Layer), §1.3 (DDD Aggregates), ADR-021. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Domain Layer (DDD), ports/, aggregates/, Domain Events, value_objects/. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Domain Layer (DDD), ports/, aggregates/, Batch Aggregate ─────────────── • add_record() • quarantine_record() • seal() • mark_committed(), PipelineRun Aggregate ─────────────── • start() • record_stage_success() • complete() • fail(), QuarantineEntry Aggregate ─────────────── • mark_retrying() • mark_recovered() • mark_dead_letter(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 09-full-er-diagram

![09-full-er-diagram](foundation/png/09-full-er-diagram.png)

- Исходная диаграмма: `mmd-diagrams/foundation/09-full-er-diagram.mmd`

## Описание
Диаграмма Title: Entity-Relationship Diagram (All Providers) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате erDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 09-full-er-diagram. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.3 (Domain Entities), §4 (Provider Specs). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `erDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 10-infrastructure-layer-class-diagram

![10-infrastructure-layer-class-diagram](foundation/png/10-infrastructure-layer-class-diagram.png)

- Исходная диаграмма: `mmd-diagrams/foundation/10-infrastructure-layer-class-diagram.mmd`

## Описание
Диаграмма Title: Infrastructure Layer Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 10-infrastructure-layer-class-diagram. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Infrastructure Layer), §3.6 (Resilience). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 11-lock-acquisition-sequence

![11-lock-acquisition-sequence](foundation/png/11-lock-acquisition-sequence.png)

- Исходная диаграмма: `mmd-diagrams/foundation/11-lock-acquisition-sequence.mmd`

## Описание
Диаграмма Title: Lock Acquisition Sequence (Two Workers) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 11-lock-acquisition-sequence. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.3 (Locking), ADR-010. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: Worker A (owner_a_uuid), Worker B (owner_b_uuid), MemoryLock, Heartbeat Thread A, SilverWriter. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 12-local-deployment-architecture

![12-local-deployment-architecture](foundation/png/12-local-deployment-architecture.png)

- Исходная диаграмма: `mmd-diagrams/foundation/12-local-deployment-architecture.mmd`

## Описание
Диаграмма Title: Local Deployment Architecture из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 12-local-deployment-architecture. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §5.6 (Deployment), ADR-010 (Local-Only). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External APIs, Local Machine (Single Instance), CLI Execution, Local Pipeline Workers, In-Process Locking. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External APIs, 🌐 ChEMBL API ebi.ac.uk/chembl, 🌐 PubChem API pubchem.ncbi.nlm.nih.gov, 🌐 UniProt API uniprot.org, 🌐 PubMed API eutils.ncbi.nlm.nih.gov, Local Machine (Single Instance). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 13-domain-models-relationship

![13-domain-models-relationship](foundation/png/13-domain-models-relationship.png)

- Исходная диаграмма: `mmd-diagrams/foundation/13-domain-models-relationship.mmd`

## Описание
Диаграмма Title: Domain Models Relationship Hierarchy из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 13-domain-models-relationship. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.3 (Domain Entities), §1.1 (Domain Layer). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 14-provider-health-states

![14-provider-health-states](foundation/png/14-provider-health-states.png)

- Исходная диаграмма: `mmd-diagrams/foundation/14-provider-health-states.mmd`

## Описание
Диаграмма Title: Provider Health State Machine из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 14-provider-health-states. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.6 (Resilience), §4 (Provider Specifications). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 15-dq-check-workflow

![15-dq-check-workflow](foundation/png/15-dq-check-workflow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/15-dq-check-workflow.mmd`

## Описание
Диаграмма Title: Data Quality Check Workflow из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 15-dq-check-workflow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.1 (DQ Checks), §2.3 (Quarantine). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Input Stage, Validation Stage, Error Classification, Action Paths, Record Routing. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Input Stage, Validation Stage, 🔍 Pandera Schema Validation, Check required fields, Validate data types, Check value constraints. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 16-memory-lock-class

![16-memory-lock-class](foundation/png/16-memory-lock-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/16-memory-lock-class.mmd`

## Описание
Диаграмма Title: MemoryLock Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 16-memory-lock-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.3 (Locking), ADR-010. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 17-pipeline-hierarchy

![17-pipeline-hierarchy](foundation/png/17-pipeline-hierarchy.png)

- Исходная диаграмма: `mmd-diagrams/foundation/17-pipeline-hierarchy.mmd`

## Описание
Диаграмма Title: Pipeline and Transformer Class Hierarchy из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 17-pipeline-hierarchy. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Pipeline Execution), §2.8 (Transformation). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 18-bronze-write-sequence

![18-bronze-write-sequence](foundation/png/18-bronze-write-sequence.png)

- Исходная диаграмма: `mmd-diagrams/foundation/18-bronze-write-sequence.mmd`

## Описание
Диаграмма Title: Bronze Write Sequence (JSONL + zstd) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 18-bronze-write-sequence. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Bronze Layer), §2.2 (Append-Only). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: PipelineExecutor, BronzeWriter, LockPort, zstd Compressor, Local FS. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 19-delta-lake-write-sequence

![19-delta-lake-write-sequence](foundation/png/19-delta-lake-write-sequence.png)

- Исходная диаграмма: `mmd-diagrams/foundation/19-delta-lake-write-sequence.mmd`

## Описание
Диаграмма Title: Delta Lake Write Sequence (Silver Layer) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 19-delta-lake-write-sequence. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Silver Layer), §2.5 (ACID via Delta Lake). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: RecordProcessor, SilverWriter, LockPort, PyArrow, deltalake (Rust). По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 20-quarantine-record-states

![20-quarantine-record-states](foundation/png/20-quarantine-record-states.png)

- Исходная диаграмма: `mmd-diagrams/foundation/20-quarantine-record-states.mmd`

## Описание
Диаграмма Title: Quarantine Record State Machine из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 20-quarantine-record-states. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.3 (Quarantine), §3.1 (Error Classification). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 21-activity-entity-data-flow

![21-activity-entity-data-flow](foundation/png/21-activity-entity-data-flow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/21-activity-entity-data-flow.mmd`

## Описание
Диаграмма Title: Activity Entity Data Flow (Extract → Transform → Load) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 21-activity-entity-data-flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.8 (Transformation), §4.1 (ChEMBL Activity). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: External API, Extract Phase, Transform Phase, Validate Phase, Load Phase. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: External API, 🌐 ChEMBL API /activities endpoint, Extract Phase, 📥 Fetch activity_id batch (ChemblAdapter), 🔗 Fetch related entities assay_id, molecule_id, target_id, 💾 Write Bronze JSONL + zstd. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 22-client-api-request-sequence

![22-client-api-request-sequence](foundation/png/22-client-api-request-sequence.png)

- Исходная диаграмма: `mmd-diagrams/foundation/22-client-api-request-sequence.mmd`

## Описание
Диаграмма Title: HTTP Client API Request Sequence из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 22-client-api-request-sequence. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.6 (Resilience), §3.7 (Rate Limiting). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: PipelineExecutor, ChemblAdapter, CircuitBreaker, TokenBucket (RateLimiter), UnifiedHTTPClient. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 23-silver-writer-class

![23-silver-writer-class](foundation/png/23-silver-writer-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/23-silver-writer-class.mmd`

## Описание
Диаграмма Title: SilverWriter Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 23-silver-writer-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Silver Layer), §2.5 (ACID via Delta Lake). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 24-hash-service-class

![24-hash-service-class](foundation/png/24-hash-service-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/24-hash-service-class.mmd`

## Описание
Диаграмма Title: ContentHashService Class Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 24-hash-service-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.4 (Deduplication via content_hash). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 25-circuit-breaker-observer-class

![25-circuit-breaker-observer-class](foundation/png/25-circuit-breaker-observer-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/25-circuit-breaker-observer-class.mmd`

## Описание
Диаграмма Title: Circuit Breaker and Observer Classes из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 25-circuit-breaker-observer-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.6 (Resilience), ADR-007. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 26-hexagonal-ports-adapters

![26-hexagonal-ports-adapters](foundation/png/26-hexagonal-ports-adapters.png)

- Исходная диаграмма: `mmd-diagrams/foundation/26-hexagonal-ports-adapters.mmd`

## Описание
Диаграмма Title: Hexagonal Architecture — Ports and Adapters Overview из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 26-hexagonal-ports-adapters. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.2 (Ports & Adapters), §1.1 (Five-Layer Architecture). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Domain Layer — Ports (Protocol), Data Ports, Coordination Ports, Observability Ports, Quality & Security Ports. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Domain Layer — Ports (Protocol), Data Ports, DataSourcePort • fetch() → AsyncIterator • health_check() → HealthStatus, FilterableDataSourcePort • fetch_filtered(), StoragePort • write_bronze() • write_silver() • write_gold(), DeltaReaderPort • read_table() • get_schema(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 27-import-matrix-enforcement

![27-import-matrix-enforcement](foundation/png/27-import-matrix-enforcement.png)

- Исходная диаграмма: `mmd-diagrams/foundation/27-import-matrix-enforcement.mmd`

## Описание
Диаграмма Title: Five-Layer Import Matrix Enforcement (ARCH-001) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 27-import-matrix-enforcement. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1, ai-selfreview-rules.md ARCH-001. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Legend, BioETL Five-Layer Architecture, Enforcement Mechanism. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Legend, ✅ Allowed Import, ❌ Forbidden Import, BioETL Five-Layer Architecture, <b>Interfaces Layer</b> CLI (Click), HealthServer <i>src/bioetl/interfaces/</i>, <b>Composition Layer</b> GenericPipelineFactory, RunnerFactory ServicesBuilder, PipelineRegistry <i>src/bioetl/composition/</i>. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 28-composition-root-di-graph

![28-composition-root-di-graph](foundation/png/28-composition-root-di-graph.png)

- Исходная диаграмма: `mmd-diagrams/foundation/28-composition-root-di-graph.mmd`

## Описание
Диаграмма Title: Composition Root Wiring — Full DI Graph из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 28-composition-root-di-graph. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Composition Layer), ADR-005. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Entry Point, Composition Factories, Logger & Observability, Client & Data Source, Storage & Services. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Entry Point, CLI run command, bootstrap/runtime/assembly.py, Composition Factories, Logger & Observability, BootstrapLogger • configure structlog. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 29-composite-pipeline-workflow

![29-composite-pipeline-workflow](foundation/png/29-composite-pipeline-workflow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/29-composite-pipeline-workflow.mmd`

## Описание
Диаграмма Title: Composite Pipeline Full Workflow — Seed to Gold (ADR-026) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 29-composite-pipeline-workflow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.10 (Composite Pipelines), ADR-026. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Phase 1: Initialization, Phase 2: Seed Pipeline, Phase 3: Dependencies, Phase 3.5: Key Extraction, Phase 4: Fan-Out Enrichment. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Phase 1: Initialization, [S] Load CompositeConfig from YAML, [S] CompositePreflightValidator • validate seed • validate enrichers • check silver tables, [S] bootstrap_composite_runner() → CompositePipelineRunner, Phase 2: Seed Pipeline, [S] Run Seed Pipeline (e.g., chembl_publication). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 30-port-adapter-mapping

![30-port-adapter-mapping](foundation/png/30-port-adapter-mapping.png)

- Исходная диаграмма: `mmd-diagrams/foundation/30-port-adapter-mapping.mmd`

## Описание
Диаграмма Title: Port-to-Adapter Mapping Table Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 30-port-adapter-mapping. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.2 (Ports & Adapters), ARCH-008 (Single Source). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Domain Ports (domain/ports/), Core Data & State, Observability & DQ, Validation & Policy, Runtime Controls. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Domain Ports (domain/ports/), Core Data & State, [P] DataSourcePort, [P] FilterableDataSourcePort, [P] StoragePort, [P] LockPort. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`

<div style="page-break-after: always;"></div>

---

## 31-pipeline-run-lifecycle

![31-pipeline-run-lifecycle](foundation/png/31-pipeline-run-lifecycle.png)

- Исходная диаграмма: `mmd-diagrams/foundation/31-pipeline-run-lifecycle.mmd`

## Описание
Диаграмма Title: Pipeline Run Lifecycle — From Config to Completion из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 31-pipeline-run-lifecycle. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3 (Execution), domain/aggregates/pipeline_run.py. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 32-single-record-journey

![32-single-record-journey](foundation/png/32-single-record-journey.png)

- Исходная диаграмма: `mmd-diagrams/foundation/32-single-record-journey.mmd`

## Описание
Диаграмма Title: Record Processing Pipeline — Single Record Journey из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 32-single-record-journey. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1-§2.6 (Data Flow, DQ), §2.8 (Normalization). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: 1. External API, 2. Bronze Layer, 3. Transform (RecordProcessor), 4. Validate, 5. Route Decision. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: 1. External API, REST API Response (e.g., ChEMBL /activity), 2. Bronze Layer, BronzeWriter.write_bronze() • JSONL serialization • zstd compression • atomic rename • _manifest.json, 3. Transform (RecordProcessor), BatchTransformer.transform(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 33-cli-run-interaction

![33-cli-run-interaction](foundation/png/33-cli-run-interaction.png)

- Исходная диаграмма: `mmd-diagrams/foundation/33-cli-run-interaction.mmd`

## Описание
Диаграмма Title: CLI Run Command → PipelineRunner Full Interaction из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 33-cli-run-interaction. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Interfaces → Composition → Application). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: User, CLI (Click) interfaces/cli/, PipelineRunnerService application/services/, bootstrap_pipeline() composition/bootstrap/, RunnerFactory composition/factories/. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 34-batch-processing-flow

![34-batch-processing-flow](foundation/png/34-batch-processing-flow.png)

- Исходная диаграмма: `mmd-diagrams/foundation/34-batch-processing-flow.mmd`

## Описание
Диаграмма Title: Batch Processing Flow — Extract to Write из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 34-batch-processing-flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Data Flow), application/core/batch_executor.py. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: PipelineRunner, BatchExecutor (786 LOC), DataSourcePort (e.g., ChemblAdapter), BatchTransformer, BaseTransformer (e.g., ActivityTransformer). По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Показательные узлы диаграммы: batch. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 36-architecture-principles-mindmap

![36-architecture-principles-mindmap](foundation/png/36-architecture-principles-mindmap.png)

- Исходная диаграмма: `mmd-diagrams/foundation/36-architecture-principles-mindmap.mmd`

## Описание
Диаграмма Title: Architecture Principles Mind Map из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате mindmap и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 36-architecture-principles-mindmap. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1 (Architecture), all ADRs. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `mindmap`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 37-cli-entry-full-chain

![37-cli-entry-full-chain](foundation/png/37-cli-entry-full-chain.png)

- Исходная диаграмма: `mmd-diagrams/foundation/37-cli-entry-full-chain.mmd`

## Описание
Диаграмма Title: CLI Entry Point to Pipeline Execution Full Chain из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 37-cli-entry-full-chain. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Interfaces Layer), interfaces/cli/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Interfaces Layer (Click), Application Service Layer, Composition Layer, Application Core, Result & Exit. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Interfaces Layer (Click), $ bioetl run --pipeline chembl_activity\n--run-type incremental\n--resume, Parse CLI Arguments • pipeline_name • run_type (RunType enum) • resume flag, Build RunOptions • pipeline_name • run_type • resume: bool, Application Service Layer, PipelineRunnerService.run() • lookup pipeline in registry • validate run options. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 38-runtime-assembly-sequence

![38-runtime-assembly-sequence](foundation/png/38-runtime-assembly-sequence.png)

- Исходная диаграмма: `mmd-diagrams/foundation/38-runtime-assembly-sequence.mmd`

## Описание
Диаграмма Title: Runtime Assembly Sequence — bootstrap/runtime/assembly.py из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 38-runtime-assembly-sequence. В комментариях исходника зафиксирован фокус диаграммы: Covers: composition/bootstrap/runtime/assembly.py, ADR-005. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: Caller (PipelineRunnerService), assembly.py, BootstrapLogger, ConfigLoader, ObservabilityBundle. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 39-medallion-invariants

![39-medallion-invariants](foundation/png/39-medallion-invariants.png)

- Исходная диаграмма: `mmd-diagrams/foundation/39-medallion-invariants.mmd`

## Описание
Диаграмма Title: Medallion Architecture Invariants (ARCH-007) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 39-medallion-invariants. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Medallion), ARCH-007 clear policy. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: RunType Enum (domain/types.py), MedallionLifecycleService\n(application/services/medallion_lifecycle.py), INCREMENTAL Path, BACKFILL Path, REBUILD Path. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: RunType Enum (domain/types.py), RunType.INCREMENTAL 'Fetch new data since last run', RunType.BACKFILL 'Re-fetch a date range', RunType.REBUILD 'Full clean rebuild', MedallionLifecycleService\n(application/services/medallion_lifecycle.py), Check RunType. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 40-application-core-collaboration

![40-application-core-collaboration](foundation/png/40-application-core-collaboration.png)

- Исходная диаграмма: `mmd-diagrams/foundation/40-application-core-collaboration.mmd`

## Описание
Диаграмма Title: Application Core Component Collaboration из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 40-application-core-collaboration. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Application Layer), application/core/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: PipelineRunner (application/core/runner.py), Lifecycle Services, Pre/Post Services, Batch Execution, Observability. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: PipelineRunner (application/core/runner.py), run() — main orchestrator, Lifecycle Services, LockCoordinator • acquire(key, owner, ttl=90s) • release(key, owner) • validate_ownership(), HeartbeatService • start() • stop(), CheckpointManager • read_checkpoint() • save_checkpoint(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 41-error-classification-tree

![41-error-classification-tree](foundation/png/41-error-classification-tree.png)

- Исходная диаграмма: `mmd-diagrams/foundation/41-error-classification-tree.mmd`

## Описание
Диаграмма Title: Error Classification Decision Tree — Full Logic из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 41-error-classification-tree. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.1 (Error Handling), domain/exceptions/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: HTTP Branch Outcomes, Domain Branch Outcomes, Infrastructure Branch Outcomes, Error Actions. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Error Occurred, HTTP Status Code?, Domain Error?, Infrastructure Error?, [E] ServiceAuthenticationError\n(CriticalError)\n→ FAIL FAST, no retry\n→ Check API key config, [E] ApiError\n(RecoverableError)\n→ Log warning\n→ Skip entity. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 42-pipeline-runner-class

![42-pipeline-runner-class](foundation/png/42-pipeline-runner-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/42-pipeline-runner-class.mmd`

## Описание
Диаграмма Title: PipelineRunner Internal Component Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 42-pipeline-runner-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: application/core/runner.py, application/core/pipeline_services.py. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 43-fan-out-fan-in-pattern

![43-fan-out-fan-in-pattern](foundation/png/43-fan-out-fan-in-pattern.png)

- Исходная диаграмма: `mmd-diagrams/foundation/43-fan-out-fan-in-pattern.mmd`

## Описание
Диаграмма Title: Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 43-fan-out-fan-in-pattern. В комментариях исходника зафиксирован фокус диаграммы: Covers: ADR-026 (Composite Pipeline Pattern), application/composite/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Seed Pipeline Result, Key Extraction, Fan-Out (EnrichmentCoordinator), Enricher Silver Tables, Fan-In (MergeService). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Seed Pipeline Result, Seed Silver Table (e.g., chembl/publication ), Key Extraction, KeyExtractorService.extract_keys() • read seed Silver via DeltaReader • select join_key columns (doi, pmid) • deduplicate → unique key list, DOI Keys (~50,000 unique), PMID Keys (~30,000 unique). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 44-cross-provider-enrichment

![44-cross-provider-enrichment](foundation/png/44-cross-provider-enrichment.png)

- Исходная диаграмма: `mmd-diagrams/foundation/44-cross-provider-enrichment.mmd`

## Описание
Диаграмма Title: Cross-Provider Data Enrichment Flow — Publication из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 44-cross-provider-enrichment. В комментариях исходника зафиксирован фокус диаграммы: Covers: ADR-026 (Composite), publication composite pipeline config. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: ChEMBL (Seed), CrossRef (Enricher), PubMed (Enricher), OpenAlex (Enricher), Semantic Scholar (Enricher). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: ChEMBL (Seed), ChemblAdapter /document endpoint, PublicationTransformer, CrossRef (Enricher), CrossRefAdapter /works?filter=doi:..., CrossRefPublicationTransformer. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 46-yaml-config-resolution

![46-yaml-config-resolution](foundation/png/46-yaml-config-resolution.png)

- Исходная диаграмма: `mmd-diagrams/foundation/46-yaml-config-resolution.mmd`

## Описание
Диаграмма Title: YAML Configuration Resolution Chain из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 46-yaml-config-resolution. В комментариях исходника зафиксирован фокус диаграммы: Covers: infrastructure/config_loader.py, infrastructure/config/, domain/config/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: YAML File Hierarchy, DQ Config Hierarchy (DQConfigLoader), Filter Config Hierarchy (FilterConfigLoader), Infrastructure Config Loaders, Domain Config Objects (Frozen). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: YAML File Hierarchy, configs/base/pipeline.yaml (global defaults), configs/providers/{provider}.yaml (provider defaults), configs/entities/{provider}/{entity}.yaml (pipeline config), configs/providers/{provider}.yaml (source config), DQ Config Hierarchy (DQConfigLoader). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`

<div style="page-break-after: always;"></div>

---

## 47-publication-merge-sources

![47-publication-merge-sources](foundation/png/47-publication-merge-sources.png)

- Исходная диаграмма: `mmd-diagrams/foundation/47-publication-merge-sources.mmd`

## Описание
Диаграмма Title: Publication Composite — Merge All Sources из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 47-publication-merge-sources. В комментариях исходника зафиксирован фокус диаграммы: Covers: application/composite/merger.py, composite/coordinator.py, composite configs. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: CLI (run-composite), CompositePipelineRunner, FSMStateHelper, PipelineRunner (chembl_document), KeyExtractorService. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 48-composite-phase-lifecycle

![48-composite-phase-lifecycle](foundation/png/48-composite-phase-lifecycle.png)

- Исходная диаграмма: `mmd-diagrams/foundation/48-composite-phase-lifecycle.mmd`

## Описание
Диаграмма Title: Composite Pipeline Phase Lifecycle (FSM) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 48-composite-phase-lifecycle. В комментариях исходника зафиксирован фокус диаграммы: Covers: domain/composite/state.py, application/composite/fsm_helper.py. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 49-composite-runner-class

![49-composite-runner-class](foundation/png/49-composite-runner-class.png)

- Исходная диаграмма: `mmd-diagrams/foundation/49-composite-runner-class.mmd`

## Описание
Диаграмма Title: CompositePipelineRunner — Component Diagram из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате classDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 49-composite-runner-class. В комментариях исходника зафиксирован фокус диаграммы: Covers: application/composite/ (runner, coordinator, merger, checkpoint, etc.). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

<div style="page-break-after: always;"></div>

---

## 50-exception-hierarchy

![50-exception-hierarchy](foundation/png/50-exception-hierarchy.png)

- Исходная диаграмма: `mmd-diagrams/foundation/50-exception-hierarchy.mmd`

## Описание
Диаграмма Title: Exception Hierarchy — Full Tree из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 50-exception-hierarchy. В комментариях исходника зафиксирован фокус диаграммы: Covers: domain/exceptions/ (base, network, validation, internal, infrastructure, data_quality). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Показательные узлы диаграммы: Exception (Python built-in), BioETLError domain/exceptions/base.py error_type: ErrorType context: dict, CriticalError error_type = CRITICAL Action: ABORT pipeline, RecoverableError error_type = RECOVERABLE Action: RETRY with backoff, DataQualityError error_type = DATA_QUALITY Action: QUARANTINE record, InvalidStateError current_state, attempted_operation. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`

