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

## C4 Container Diagram

For a more detailed look at the runtime instances and interactions between the services, see the C4 Container Diagram.

*   **[C4: Диаграмма Контейнеров](container-diagram.md)**
