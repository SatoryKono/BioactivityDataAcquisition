______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Diagrams

## High-Level Architecture

> **Diagram:** See [`01-high-level-hexagonal.mmd`](../architecture/01-high-level-hexagonal.mmd)

## Medallion Architecture

> **Diagram:** See [`03-medallion-data-flow.mmd`](../architecture/03-medallion-data-flow.mmd)

## Class Diagram

> **Diagram:** See [`07-application-core-services.mmd`](../class-diagrams/07-application-core-services.mmd)

## Layer Interaction

Shows how BioETL layers communicate following Hexagonal Architecture:

> **Diagram:** See [`02-layer-dependency-matrix.mmd`](../architecture/02-layer-dependency-matrix.mmd)

## Pipeline Execution Sequence

Shows the complete execution flow from CLI to data storage:

> **Diagram:** See [`04-pipeline-execution-flow.mmd`](../architecture/04-pipeline-execution-flow.mmd)

## Medallion Data Flow

Shows data transformation through Bronze → Silver → Gold layers:

> **Diagram:** See [`03-medallion-data-flow.mmd`](../architecture/03-medallion-data-flow.mmd)
> *(detailed version with DQ and quarantine)*

## Domain Layer (DDD)

Shows the DDD components in the domain layer:

```mermaid
flowchart TB
    subgraph domain["Domain Layer"]
        subgraph aggregates["DDD Aggregates"]
            Batch["Batch
            ─────────
            add-record()
            quarantine-record()
            seal()
            mark-committed()"]

            PipelineRun["PipelineRun
            ─────────
            start()
            record-stage-success()
            complete()
            fail()"]
        end

        subgraph events["Domain Events"]
            BatchCreated
            BatchSealed
            BatchWritten
            RunStarted
            RunCompleted
        end

        subgraph value-objects["Value Objects"]
            RunID["RunID"]
            BatchID["BatchID"]
            EntityID["EntityID"]
            ContentHash["ContentHash"]
        end

        subgraph ports["Ports"]
            BronzeStoragePort
            SilverStoragePort
            GoldStoragePort
            MergedStoragePort
            LockPort
            CheckpointPort
            DataSourcePort
        end
    end

    Batch --> BatchCreated
    Batch --> BatchSealed
    Batch --> BatchWritten
    PipelineRun --> RunStarted
    PipelineRun --> RunCompleted
    Batch --> RunID
    Batch --> BatchID
    PipelineRun --> RunID
```

See [ADR-021: DDD Aggregates Adoption](../../decisions/ADR-021-ddd-aggregates-adoption.md) for details.

## Batch State Machine

```mermaid
stateDiagram-v2
    [*] --> OPEN: create()
    OPEN --> SEALED: seal()
    SEALED --> WRITING: mark-writing()
    WRITING --> COMMITTED: mark-committed()
    WRITING --> FAILED: mark-failed()
    COMMITTED --> [*]
    FAILED --> [*]

    note right of OPEN : Records can be added
    note right of SEALED : No more records
    note right of WRITING : Writing to storage
```

## PipelineRun State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: create()
    PENDING --> RUNNING: start()
    RUNNING --> COMPLETED: complete()
    RUNNING --> FAILED: fail()
    RUNNING --> SHUTDOWN: shutdown()
    COMPLETED --> [*]
    FAILED --> [*]
    SHUTDOWN --> [*]

    note right of RUNNING : Stages executing
    note right of SHUTDOWN : Graceful stop
```

## C4 Container Diagram

For a more detailed look at the runtime instances and interactions between the services, see the C4 Container Diagram.

- **[C4: Диаграмма Контейнеров](container-reference.md)**
