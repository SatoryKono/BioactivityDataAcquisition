# Diagrams

## High-Level Architecture

```mermaid
flowchart TD
    subgraph "External Sources"
        A[Public APIs e.g., ChEMBL]
    end

    subgraph "BioETL Application"
        B(Orchestrator)
        C(Extractor)
        D(Transformer)
        E(Loader)
    end

    subgraph "Composition Layer"
        CP[Bootstrap / Factories]
    end

    CLI --> CP
    CP --> B

    subgraph "Data Lake (Medallion)"
        F[Bronze Layer]
        G[Silver Layer]
        H[Gold Layer]
    end

    A --> C
    B --> C
    C --> F
    F --> D
    D --> G
    G --> H
    D --> E
    E --> G
```

## Medallion Architecture

```mermaid
flowchart LR
    subgraph Sources["External Sources"]
        SRC1["ChEMBL"]
        SRC2["PubChem"]
        SRC3["UniProt"]
    end

    subgraph Bronze["Bronze Layer"]
        direction TB
        B1["JSONL + zstd"]
        B2["Append-only"]
        B3["90 days retention"]
    end

    subgraph Silver["Silver Layer"]
        direction TB
        S1["Delta Lake"]
        S2["Merge/Upsert"]
        S3["Permanent"]
    end

    subgraph Gold["Gold Layer"]
        direction TB
        G1["Delta / Parquet"]
        G2["SCD Type 2"]
        G3["Permanent"]
    end

    subgraph Side["Side Tables"]
        Q["Quarantine<br/>(DQ failures)"]
        L["Lineage Log<br/>(Provenance)"]
    end

    Sources -->|REST API| Bronze
    Bronze -->|Transform + Validate| Silver
    Silver -->|Aggregate| Gold
    Silver -.->|DQ errors| Q
    Bronze -.->|batch_id FK| L
```

## Class Diagram

```mermaid
classDiagram
    class BioEtlPipeline {
        +run()
    }

    class Extractor {
        +extract()
    }

    class Transformer {
        +transform()
    }

    class Loader {
        +load()
    }

    class DataLake {
        +write()
        +read()
    }

    BioEtlPipeline --> Extractor
    BioEtlPipeline --> Transformer
    BioEtlPipeline --> Loader
    Extractor --> DataLake
    Transformer --> DataLake
    Loader --> DataLake
```

## Layer Interaction

Shows how BioETL layers communicate following Hexagonal Architecture:

```mermaid
flowchart TB
    subgraph Interfaces["Interfaces Layer"]
        CLI[CLI Entry Point]
    end

    subgraph Composition["Composition Layer"]
        Bootstrap[bootstrap_pipeline]
        Factories[Factories]
    end

    subgraph Application["Application Layer"]
        Runner[PipelineRunner]
        Executor[PipelineExecutor]
        Transformer[BaseTransformer]
    end

    subgraph Domain["Domain Layer"]
        Ports[Port Interfaces]
        Types[Core Types]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        Adapters[Data Source Adapters]
        Storage[Storage Writers]
    end

    CLI --> Bootstrap
    Bootstrap --> Factories
    Factories --> Runner
    Runner --> Executor
    Executor --> Transformer
    Application --> Ports
    Adapters -.->|implements| Ports
    Storage -.->|implements| Ports
```

## Pipeline Execution Sequence

Shows the complete execution flow from CLI to data storage:

```mermaid
sequenceDiagram
    autonumber
    participant CLI
    participant Runner as PipelineRunner
    participant Preflight as PreflightService
    participant Executor as PipelineExecutor
    participant DataSource
    participant Transformer
    participant Storage

    CLI->>Runner: run()
    Runner->>Preflight: execute()
    Preflight->>Storage: health_check()
    Preflight->>DataSource: health_check()
    Preflight-->>Runner: success

    Runner->>Runner: acquire_lock()
    Runner->>Executor: execute()

    loop Each Batch
        Executor->>DataSource: fetch(batch)
        Executor->>Transformer: transform(records)
        Executor->>Storage: write_bronze()
        Executor->>Storage: write_silver()
        Executor->>Storage: write_gold()
    end

    Runner->>Runner: release_lock()
    Runner-->>CLI: result
```

## Medallion Data Flow

Shows data transformation through Bronze → Silver → Gold layers:

```mermaid
flowchart LR
    subgraph Sources["External Sources"]
        ChEMBL[(ChEMBL)]
        PubChem[(PubChem)]
        UniProt[(UniProt)]
    end

    subgraph Bronze["Bronze Layer"]
        BW[BronzeWriter]
        BD[("JSONL+zstd")]
    end

    subgraph Silver["Silver Layer"]
        DW[DeltaWriter]
        SD[("Delta Lake")]
    end

    subgraph Gold["Gold Layer"]
        GW[GoldWriter]
        GD[("Delta Lake")]
    end

    Sources --> BW --> BD
    BD --> DW --> SD
    SD --> GW --> GD
```

## Domain Layer (DDD)

Shows the DDD components in the domain layer:

```mermaid
flowchart TB
    subgraph domain["Domain Layer"]
        subgraph aggregates["DDD Aggregates"]
            Batch["Batch
            ─────────
            add_record()
            quarantine_record()
            seal()
            mark_committed()"]

            PipelineRun["PipelineRun
            ─────────
            start()
            record_stage_success()
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

        subgraph value_objects["Value Objects"]
            RunID["RunID"]
            BatchID["BatchID"]
            EntityID["EntityID"]
            ContentHash["ContentHash"]
        end

        subgraph ports["Ports"]
            StoragePort
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

See [ADR-021: DDD Aggregates Adoption](decisions/ADR-021-ddd-aggregates-adoption.md) for details.

## Batch State Machine

```mermaid
stateDiagram-v2
    [*] --> OPEN: create()
    OPEN --> SEALED: seal()
    SEALED --> WRITING: mark_writing()
    WRITING --> COMMITTED: mark_committed()
    WRITING --> FAILED: mark_failed()
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

*   **[C4: Диаграмма Контейнеров](container-diagram.md)**
