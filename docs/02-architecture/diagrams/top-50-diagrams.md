# TOP-50 архитектурных диаграмм BioETL (прозрачная приоритизация)

*Версия: 2.0 | Дата: 2026-02-17*

Документ фиксирует прозрачную формулу приоритизации и явные оценки по каждому критерию для 50 первоочередных диаграмм.

## Формула приоритета

- Шкала всех критериев: **1..10** (10 = максимум ценности).
- Критерии:
  - `Arch` — архитектурная критичность (вес `2.0`)
  - `Doc` — документационная ценность (вес `1.5`)
  - `Freq` — частота использования в обсуждениях/ревью (вес `1.5`)
  - `Complex` — сложность понимания без схемы (вес `2.0`)
  - `Coverage` — охват подсистем/кода (вес `1.0`)
- **PriorityScore** = `(2*Arch + 1.5*Doc + 1.5*Freq + 2*Complex + 1*Coverage) / 8`
- Сортировка: по `PriorityScore` по убыванию, затем по `Arch`, затем по `Freq`.

## TOP-50 с явными оценками

| Rank | Диаграмма                                  | Тип        | Уровень      | Arch | Doc | Freq | Complex | Coverage | PriorityScore | Source                                          |
| ---: | ------------------------------------------ | ---------- | ------------ | ---: | --: | ---: | ------: | -------: | ------------: | ----------------------------------------------- |
|    1 | Error Classification                       | Flowchart  | L2-Component |    9 |   8 |    8 |       9 |        8 |      **8.50** | `04-error-flow.mermaid`                         |
|    2 | Delta Lake Write Sequence / Focus 22       | Sequence   | L2-Component |    9 |   9 |    9 |       9 |        5 |      **8.50** | `19-delta-lake-write-sequence.mermaid`          |
|    3 | Lock Acquisition                           | Sequence   | L2-Component |    9 |   7 |    9 |       9 |        7 |      **8.38** | `11-lock-acquisition-sequence.mermaid`          |
|    4 | Hexagonal Architecture Overview / Focus 03 | C4 Context | L0-Context   |    8 |   8 |   10 |       8 |        8 |      **8.38** | `05-layers-interaction.mermaid`                 |
|    5 | Delta Lake Write Sequence                  | Sequence   | L2-Component |    9 |   6 |   10 |       9 |        6 |      **8.25** | `19-delta-lake-write-sequence.mermaid`          |
|    6 | Ports Architecture                         | Interface  | L3-Code      |    9 |   9 |    7 |       9 |        5 |      **8.12** | `04-domain-layer-class-diagram.mermaid`         |
|    7 | PipelineRun Aggregate                      | State      | L3-Code      |   10 |   8 |   10 |       5 |        8 |      **8.12** | `05-pipeline-lifecycle-states.mermaid`          |
|    8 | Ports Architecture / Focus 07              | Interface  | L3-Code      |    9 |   8 |    6 |       9 |        8 |      **8.12** | `04-domain-layer-class-diagram.mermaid`         |
|    9 | Bronze Write Sequence                      | Sequence   | L2-Component |    8 |   9 |    9 |       8 |        5 |      **8.00** | `18-bronze-write-sequence.mermaid`              |
|   10 | Error Classification / Focus 12            | Flowchart  | L2-Component |    9 |   7 |    7 |       9 |        7 |      **8.00** | `04-error-flow.mermaid`                         |
|   11 | Bronze Write Sequence / Focus 23           | Sequence   | L2-Component |    8 |   8 |    8 |       8 |        8 |      **8.00** | `18-bronze-write-sequence.mermaid`              |
|   12 | Layer Dependency Matrix                    | Matrix     | L2-Component |    7 |   8 |   10 |       7 |        8 |      **7.88** | `05-layers-interaction.mermaid`                 |
|   13 | Lock Acquisition / Focus 17                | Sequence   | L2-Component |    9 |   6 |    8 |       9 |        6 |      **7.88** | `11-lock-acquisition-sequence.mermaid`          |
|   14 | Composition Root                           | Component  | L2-Component |   10 |   9 |    9 |       5 |        5 |      **7.75** | `01-high-level.mermaid`                         |
|   15 | Complete Pipeline Flow / Focus 02          | Flowchart  | L2-Component |    9 |   9 |    5 |       9 |        5 |      **7.75** | `03-pipeline-execution-happy-path.mermaid`      |
|   16 | Composition Root / Focus 11                | Component  | L2-Component |   10 |   8 |    8 |       5 |        8 |      **7.75** | `01-high-level.mermaid`                         |
|   17 | Batch Processing Flow                      | Activity   | L2-Component |    8 |   8 |    6 |       8 |        8 |      **7.62** | `06-pipeline-execution.mermaid`                 |
|   18 | PipelineRun Aggregate / Focus 16           | State      | L3-Code      |   10 |   7 |    9 |       5 |        7 |      **7.62** | `05-pipeline-lifecycle-states.mermaid`          |
|   19 | MemoryLock Class / Focus 18                | Class      | L3-Code      |    8 |   9 |    7 |       8 |        5 |      **7.62** | `16-memory-lock-class.mermaid`                  |
|   20 | Complete Pipeline Flow                     | Flowchart  | L2-Component |    9 |   6 |    6 |       9 |        6 |      **7.50** | `03-pipeline-execution-happy-path.mermaid`      |
|   21 | Storage Architecture                       | Component  | L2-Component |    8 |   7 |    7 |       8 |        7 |      **7.50** | `10-infrastructure-layer-class-diagram.mermaid` |
|   22 | Silver Writer Internals                    | Class      | L3-Code      |    7 |   8 |    8 |       7 |        8 |      **7.50** | `23-silver-writer-class.mermaid`                |
|   23 | Content Hash Service / Focus 21            | Class      | L3-Code      |   10 |   6 |   10 |       5 |        6 |      **7.50** | `24-hash-service-class.mermaid`                 |
|   24 | MemoryLock Class                           | Class      | L3-Code      |    8 |   6 |    8 |       8 |        6 |      **7.38** | `16-memory-lock-class.mermaid`                  |
|   25 | Layer Dependency Matrix / Focus 04         | Matrix     | L2-Component |    7 |   7 |    9 |       7 |        7 |      **7.38** | `05-layers-interaction.mermaid`                 |
|   26 | Domain Model Overview / Focus 06           | Class      | L3-Code      |   10 |   9 |    7 |       5 |        5 |      **7.38** | `08-domain-ddd.mermaid`                         |
|   27 | Circuit Breaker States / Focus 15          | State      | L3-Code      |    6 |   8 |   10 |       6 |        8 |      **7.38** | `07-circuit-breaker-states.mermaid`             |
|   28 | Five Layer Architecture                    | Component  | L1-Container |   10 |   7 |    7 |       5 |        7 |      **7.25** | `01-full-system-component.mermaid`              |
|   29 | Hexagonal Architecture Overview            | C4 Context | L0-Context   |    8 |   9 |    5 |       8 |        5 |      **7.25** | `05-layers-interaction.mermaid`                 |
|   30 | DDD Aggregates / Focus 09                  | Class      | L3-Code      |    7 |   6 |   10 |       7 |        6 |      **7.25** | `13-domain-models-relationship.mermaid`         |
|   31 | Domain Model Overview                      | Class      | L3-Code      |   10 |   6 |    8 |       5 |        6 |      **7.12** | `08-domain-ddd.mermaid`                         |
|   32 | DQ Workflow                                | Activity   | L2-Component |    7 |   9 |    7 |       7 |        5 |      **7.12** | `15-dq-check-workflow.mermaid`                  |
|   33 | Batch Processing Flow / Focus 08           | Activity   | L2-Component |    8 |   7 |    5 |       8 |        7 |      **7.12** | `06-pipeline-execution.mermaid`                 |
|   34 | DQ Workflow / Focus 19                     | Activity   | L2-Component |    7 |   8 |    6 |       7 |        8 |      **7.12** | `15-dq-check-workflow.mermaid`                  |
|   35 | Pipeline Core Components / Focus 10        | Component  | L2-Component |    6 |   9 |    9 |       6 |        5 |      **7.00** | `06-application-layer-class-diagram.mermaid`    |
|   36 | Storage Architecture / Focus 13            | Component  | L2-Component |    8 |   6 |    6 |       8 |        6 |      **7.00** | `10-infrastructure-layer-class-diagram.mermaid` |
|   37 | Silver Writer Internals / Focus 24         | Class      | L3-Code      |    7 |   7 |    7 |       7 |        7 |      **7.00** | `23-silver-writer-class.mermaid`                |
|   38 | Medallion Architecture Overview            | Flowchart  | L1-Container |    6 |   7 |    9 |       6 |        7 |      **6.88** | `02-full-medallion-data-flow.mermaid`           |
|   39 | Content Hash Service                       | Class      | L3-Code      |   10 |   7 |    5 |       5 |        7 |      **6.88** | `24-hash-service-class.mermaid`                 |
|   40 | Pipeline Core Components                   | Component  | L2-Component |    6 |   6 |   10 |       6 |        6 |      **6.75** | `06-application-layer-class-diagram.mermaid`    |
|   41 | Five Layer Architecture / Focus 01         | Component  | L1-Container |   10 |   6 |    6 |       5 |        6 |      **6.75** | `01-full-system-component.mermaid`              |
|   42 | HTTP Infrastructure / Focus 14             | Component  | L2-Component |    7 |   9 |    5 |       7 |        5 |      **6.75** | `22-client-api-request-sequence.mermaid`        |
|   43 | DDD Aggregates                             | Class      | L3-Code      |    7 |   7 |    5 |       7 |        7 |      **6.62** | `13-domain-models-relationship.mermaid`         |
|   44 | Quarantine States                          | State      | L3-Code      |    6 |   8 |    6 |       6 |        8 |      **6.62** | `20-quarantine-record-states.mermaid`           |
|   45 | HTTP Infrastructure                        | Component  | L2-Component |    7 |   6 |    6 |       7 |        6 |      **6.50** | `22-client-api-request-sequence.mermaid`        |
|   46 | CircuitBreaker Internals                   | Class      | L3-Code      |    6 |   7 |    7 |       6 |        7 |      **6.50** | `25-circuit-breaker-observer-class.mermaid`     |
|   47 | Medallion Architecture Overview / Focus 05 | Flowchart  | L1-Container |    6 |   6 |    8 |       6 |        6 |      **6.38** | `02-full-medallion-data-flow.mermaid`           |
|   48 | Circuit Breaker States                     | State      | L3-Code      |    6 |   9 |    5 |       6 |        5 |      **6.25** | `07-circuit-breaker-states.mermaid`             |
|   49 | Quarantine States / Focus 20               | State      | L3-Code      |    6 |   7 |    5 |       6 |        7 |      **6.12** | `20-quarantine-record-states.mermaid`           |
|   50 | CircuitBreaker Internals / Focus 25        | Class      | L3-Code      |    6 |   6 |    6 |       6 |        6 |      **6.00** | `25-circuit-breaker-observer-class.mermaid`     |

## Правила пересмотра оценок

- Пересчитывать таблицу при изменении архитектурных ограничений (ADR/RULES).
- Минимум раз в спринт валидировать `Freq` и `Coverage` на основе фактических ревью/инцидентов.
- Любое ручное изменение баллов сопровождать коротким обоснованием в PR.
