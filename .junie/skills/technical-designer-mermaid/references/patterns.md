# Mermaid Pattern Library (BioETL-Oriented)

Use these templates as starting points for BioETL diagrams, then adapt node names
to match actual modules/files in the repository.

## Canonical `.mmd` Header Template

```mermaid
%% BioETL - <Title>
%% <Coverage summary>
%% @version 1.0.0
%% @date 2026-02-27
%% @type flowchart
%% @level System / Component
%% @nodes 12
%% @adr ADR-040
flowchart TB
```

## Flowchart: Hexagonal 5-Layer View

```mermaid
%% BioETL - Hexagonal Layer Overview
%% @version 1.0.0
%% @date 2026-02-27
%% @type flowchart
%% @level System / Component
%% @nodes 14
%% @adr ADR-040
flowchart TB
    subgraph Interfaces
        cli["CLI Commands"]
    end
    subgraph Composition
        bootstrap["Bootstrap / Factories"]
    end
    subgraph Application
        runner["PipelineRunner"]
        executor["BatchExecutor"]
    end
    subgraph Domain
        ports["Ports (Protocols)"]
        entities["Entities / Aggregates"]
    end
    subgraph Infrastructure
        adapters["HTTP Adapters"]
        storage["Bronze/Silver/Gold Writers"]
    end
    external["External APIs"]

    cli --> bootstrap
    bootstrap --> runner
    runner --> executor
    executor -.uses.-> ports
    adapters -.implements.-> ports
    storage -.implements.-> ports
    adapters --> external
```

## Flowchart: Medallion Data Flow

```mermaid
%% BioETL - Medallion Data Flow
%% @version 1.0.0
%% @date 2026-02-27
%% @type flowchart
%% @level System / Component
%% @nodes 13
%% @adr ADR-040
flowchart LR
    source["Provider API"] --> bronze["Bronze Raw"]
    bronze --> transform["Transform + Normalize"]
    transform --> dq{"DQ Checks"}
    dq -->|pass| silver["Silver Delta"]
    dq -->|fail| quarantine["Quarantine"]
    silver --> gold["Gold Curated"]
    silver --> vacuum["VACUUM / Retention"]
```

## Sequence: CLI to Pipeline Runner

```mermaid
%% BioETL - CLI Run Sequence
%% @version 1.0.0
%% @date 2026-02-27
%% @type sequenceDiagram
%% @level Sequence
%% @nodes 10
%% @adr ADR-040
sequenceDiagram
    participant CLI as CLI
    participant Boot as Bootstrap
    participant Runner as PipelineRunner
    participant Exec as BatchExecutor
    participant Src as SourceAdapter
    participant Silver as SilverWriter

    CLI->>Boot: run --pipeline <name>
    Boot->>Runner: create runner + dependencies
    Runner->>Exec: execute batches
    loop batches
        Exec->>Src: fetch batch
        Src-->>Exec: raw records
        Exec->>Silver: merge/upsert
    end
    Runner-->>CLI: exit code + summary
```

## Class Diagram: Port to Adapter Mapping

```mermaid
%% BioETL - Port Adapter Mapping
%% @version 1.0.0
%% @date 2026-02-27
%% @type classDiagram
%% @level Class / Interface
%% @nodes 12
%% @adr ADR-040
classDiagram
    class DataSourcePort {
      <<Protocol>>
      +fetch_batch()
    }
    class StoragePort {
      <<Protocol>>
      +write_bronze()
      +write_silver()
    }
    class ChEMBLAdapter {
      +fetch_batch()
    }
    class SilverWriter {
      +write_silver()
    }
    class BronzeWriter {
      +write_bronze()
    }
    class PipelineRunner {
      +run()
    }

    DataSourcePort <|.. ChEMBLAdapter
    StoragePort <|.. SilverWriter
    StoragePort <|.. BronzeWriter
    PipelineRunner --> DataSourcePort : uses
    PipelineRunner --> StoragePort : uses
```

## State Diagram: Pipeline Run Lifecycle

```mermaid
%% BioETL - Pipeline Run Lifecycle
%% @version 1.0.0
%% @date 2026-02-27
%% @type stateDiagram
%% @level State
%% @nodes 9
%% @adr ADR-040
stateDiagram-v2
    [*] --> Created
    Created --> Running: start
    Running --> Checkpointed: checkpoint
    Checkpointed --> Running: resume
    Running --> Completed: success
    Running --> Failed: error
    Failed --> Running: retry
    Completed --> [*]
```

## Flowchart: Composite Pipeline

```mermaid
%% BioETL - Composite Pipeline Workflow
%% @version 1.0.0
%% @date 2026-02-27
%% @type flowchart
%% @level System / Component
%% @nodes 11
%% @adr ADR-026
flowchart LR
    seed["Seed Pipeline"] --> deps["Dependencies"]
    deps --> fanout["Enrichers (parallel)"]
    fanout --> merge["Merge + Cross-validation"]
    merge --> gold["Composite Gold"]
```
