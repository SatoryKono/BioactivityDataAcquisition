# BioETL Architecture Diagrams

*Updated: 2026-02-17*

В каталоге `34` исходных диаграмм Mermaid. Принята единая структура:

- `docs/02-architecture/diagrams/mermaid/` — исходники `.mermaid`.
- `docs/02-architecture/diagrams/png/` — рендеры `.png`.

## Diagram Overview

| #   | Mermaid                                                                                                  | PNG                                                                                          | Description                                 |
| --- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------- |
| 01  | [`01-full-system-component.mermaid`](mermaid/01-full-system-component.mermaid)                           | [`01-full-system-component.png`](png/01-full-system-component.png)                           | Full system component diagram (C4-style)    |
| 01  | [`01-high-level.mermaid`](mermaid/01-high-level.mermaid)                                                 | [`01-high-level.png`](png/01-high-level.png)                                                 | High-level system overview                  |
| 02  | [`02-full-medallion-data-flow.mermaid`](mermaid/02-full-medallion-data-flow.mermaid)                     | [`02-full-medallion-data-flow.png`](png/02-full-medallion-data-flow.png)                     | Medallion architecture data flow (detailed) |
| 02  | [`02-medallion.mermaid`](mermaid/02-medallion.mermaid)                                                   | [`02-medallion.png`](png/02-medallion.png)                                                   | Medallion architecture (simplified)         |
| 03  | [`03-pipeline-execution-happy-path.mermaid`](mermaid/03-pipeline-execution-happy-path.mermaid)           | [`03-pipeline-execution-happy-path.png`](png/03-pipeline-execution-happy-path.png)           | Pipeline execution sequence (happy path)    |
| 03  | [`03-pipeline-sequence.mermaid`](mermaid/03-pipeline-sequence.mermaid)                                   | [`03-pipeline-sequence.png`](png/03-pipeline-sequence.png)                                   | Pipeline sequence diagram                   |
| 04  | [`04-domain-layer-class-diagram.mermaid`](mermaid/04-domain-layer-class-diagram.mermaid)                 | [`04-domain-layer-class-diagram.png`](png/04-domain-layer-class-diagram.png)                 | Domain layer ports, entities, config        |
| 04  | [`04-error-flow.mermaid`](mermaid/04-error-flow.mermaid)                                                 | [`04-error-flow.png`](png/04-error-flow.png)                                                 | Error handling flow                         |
| 05  | [`05-layers-interaction.mermaid`](mermaid/05-layers-interaction.mermaid)                                 | [`05-layers-interaction.png`](png/05-layers-interaction.png)                                 | Layer interaction diagram                   |
| 05  | [`05-locking.mermaid`](mermaid/05-locking.mermaid)                                                       | [`05-locking.png`](png/05-locking.png)                                                       | Locking mechanism                           |
| 05  | [`05-pipeline-lifecycle-states.mermaid`](mermaid/05-pipeline-lifecycle-states.mermaid)                   | [`05-pipeline-lifecycle-states.png`](png/05-pipeline-lifecycle-states.png)                   | Pipeline state machine                      |
| 06  | [`06-application-layer-class-diagram.mermaid`](mermaid/06-application-layer-class-diagram.mermaid)       | [`06-application-layer-class-diagram.png`](png/06-application-layer-class-diagram.png)       | Application layer classes                   |
| 06  | [`06-pipeline-execution.mermaid`](mermaid/06-pipeline-execution.mermaid)                                 | [`06-pipeline-execution.png`](png/06-pipeline-execution.png)                                 | Pipeline execution flow                     |
| 07  | [`07-circuit-breaker-states.mermaid`](mermaid/07-circuit-breaker-states.mermaid)                         | [`07-circuit-breaker-states.png`](png/07-circuit-breaker-states.png)                         | Circuit breaker state machine               |
| 07  | [`07-medallion-flow.mermaid`](mermaid/07-medallion-flow.mermaid)                                         | [`07-medallion-flow.png`](png/07-medallion-flow.png)                                         | Medallion data flow                         |
| 08  | [`08-complete-etl-workflow.mermaid`](mermaid/08-complete-etl-workflow.mermaid)                           | [`08-complete-etl-workflow.png`](png/08-complete-etl-workflow.png)                           | Complete ETL workflow                       |
| 08  | [`08-domain-ddd.mermaid`](mermaid/08-domain-ddd.mermaid)                                                 | [`08-domain-ddd.png`](png/08-domain-ddd.png)                                                 | Domain-driven design diagram                |
| 09  | [`09-full-er-diagram.mermaid`](mermaid/09-full-er-diagram.mermaid)                                       | [`09-full-er-diagram.png`](png/09-full-er-diagram.png)                                       | Entity-relationship diagram                 |
| 10  | [`10-infrastructure-layer-class-diagram.mermaid`](mermaid/10-infrastructure-layer-class-diagram.mermaid) | [`10-infrastructure-layer-class-diagram.png`](png/10-infrastructure-layer-class-diagram.png) | Infrastructure layer classes                |
| 11  | [`11-lock-acquisition-sequence.mermaid`](mermaid/11-lock-acquisition-sequence.mermaid)                   | [`11-lock-acquisition-sequence.png`](png/11-lock-acquisition-sequence.png)                   | Lock acquisition sequence                   |
| 12  | [`12-full-aws-deployment.mermaid`](mermaid/12-full-aws-deployment.mermaid)                               | [`12-full-aws-deployment.png`](png/12-full-aws-deployment.png)                               | AWS deployment (legacy reference)           |
| 13  | [`13-domain-models-relationship.mermaid`](mermaid/13-domain-models-relationship.mermaid)                 | [`13-domain-models-relationship.png`](png/13-domain-models-relationship.png)                 | Domain model relationships                  |
| 14  | [`14-provider-health-states.mermaid`](mermaid/14-provider-health-states.mermaid)                         | [`14-provider-health-states.png`](png/14-provider-health-states.png)                         | Provider health states                      |
| 15  | [`15-dq-check-workflow.mermaid`](mermaid/15-dq-check-workflow.mermaid)                                   | [`15-dq-check-workflow.png`](png/15-dq-check-workflow.png)                                   | Data quality check workflow                 |
| 16  | [`16-memory-lock-class.mermaid`](mermaid/16-memory-lock-class.mermaid)                                   | [`16-memory-lock-class.png`](png/16-memory-lock-class.png)                                   | MemoryLock class diagram                    |
| 17  | [`17-pipeline-hierarchy.mermaid`](mermaid/17-pipeline-hierarchy.mermaid)                                 | [`17-pipeline-hierarchy.png`](png/17-pipeline-hierarchy.png)                                 | Pipeline/Transformer hierarchy              |
| 18  | [`18-bronze-write-sequence.mermaid`](mermaid/18-bronze-write-sequence.mermaid)                           | [`18-bronze-write-sequence.png`](png/18-bronze-write-sequence.png)                           | Bronze write sequence                       |
| 19  | [`19-delta-lake-write-sequence.mermaid`](mermaid/19-delta-lake-write-sequence.mermaid)                   | [`19-delta-lake-write-sequence.png`](png/19-delta-lake-write-sequence.png)                   | Delta Lake write sequence                   |
| 20  | [`20-quarantine-record-states.mermaid`](mermaid/20-quarantine-record-states.mermaid)                     | [`20-quarantine-record-states.png`](png/20-quarantine-record-states.png)                     | Quarantine record states                    |
| 21  | [`21-activity-entity-data-flow.mermaid`](mermaid/21-activity-entity-data-flow.mermaid)                   | [`21-activity-entity-data-flow.png`](png/21-activity-entity-data-flow.png)                   | Activity entity data flow                   |
| 22  | [`22-client-api-request-sequence.mermaid`](mermaid/22-client-api-request-sequence.mermaid)               | [`22-client-api-request-sequence.png`](png/22-client-api-request-sequence.png)               | Client API request sequence                 |
| 23  | [`23-silver-writer-class.mermaid`](mermaid/23-silver-writer-class.mermaid)                               | [`23-silver-writer-class.png`](png/23-silver-writer-class.png)                               | SilverWriter class diagram                  |
| 24  | [`24-hash-service-class.mermaid`](mermaid/24-hash-service-class.mermaid)                                 | [`24-hash-service-class.png`](png/24-hash-service-class.png)                                 | Hash service class diagram                  |
| 25  | [`25-circuit-breaker-observer-class.mermaid`](mermaid/25-circuit-breaker-observer-class.mermaid)         | [`25-circuit-breaker-observer-class.png`](png/25-circuit-breaker-observer-class.png)         | CircuitBreaker observer class diagram       |

## Definition of Done для новой диаграммы

- [ ] Добавлен исходник `.mermaid` в `docs/02-architecture/diagrams/mermaid/`.
- [ ] Сгенерирован `.png` в `docs/02-architecture/diagrams/png/`.
- [ ] Добавлена строка в этот индекс (`diagrams-index.md`).
- [ ] На архитектурной странице `docs/02-architecture/*.md` есть контекстный абзац со ссылкой на диаграмму.

## Rendering to PNG

```bash
cd docs/02-architecture/diagrams
./render_diagrams.sh
```
