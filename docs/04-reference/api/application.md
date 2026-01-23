# Application Layer

The Application layer contains pipeline orchestration, use cases, and data transformation logic. It depends only on the Domain layer.

## Overview

```mermaid
flowchart TB
    subgraph Application["Application Layer"]
        subgraph Core["Core"]
            Runner[PipelineRunner]
            Executor[PipelineExecutor]
            Services[PipelineServices]
        end

        subgraph AppServices["Services"]
            Medallion[MedallionLifecycle]
            DQ[DQService]
            Health[HealthService]
        end

        subgraph Transform["Transformation"]
            BaseT[BaseTransformer]
            BatchT[BatchTransformer]
        end

        subgraph Pipelines["Pipelines"]
            ChEMBL[ChEMBL Pipelines]
            PubChem[PubChem Pipeline]
            UniProt[UniProt Pipeline]
            PubMed[PubMed Pipeline]
        end

        Runner --> Executor
        Executor --> Services
        Runner --> Medallion
        Runner --> DQ
        BaseT --> BatchT
        Pipelines --> BaseT
    end

    Application --> Domain["Domain Layer"]
```

## Modules

### [Core](application/core.md)

Pipeline execution infrastructure:

- `PipelineRunner` - Lifecycle orchestrator for pipeline execution
- `PipelineExecutor` - Data flow orchestrator (fetch → transform → write)
- `PipelineServices` - Service bundle for dependency injection
- `CheckpointManager` - Checkpoint persistence for resume capability
- `LockManager` - Distributed locking coordination
- `PreflightService` - Pre-flight infrastructure validation
- `PostrunService` - Post-run DQ checks, VACUUM, cleanup

### [Services](application/services.md)

Specialized application services:

- `MedallionLifecycleService` - Medallion layer management
- `DataQualityService` - DQ checks and validation orchestration
- `HealthService` - System health aggregation
- `VacuumService` - Storage maintenance
- `LockService`, `CheckpointService`, `ShutdownService` - Infrastructure services

### [Transformers](application/transformers.md)

Data transformation framework:

- `BaseTransformer` - Template Method pattern for Bronze → Silver → Gold
- `BatchTransformer` - Batch-oriented transformation
- Transform utilities - Common transformation helpers

### [Pipelines](application/pipelines.md)

Provider-specific pipeline implementations:

- **ChEMBL**: Activity, Assay, Molecule, Target, Document
- **PubChem**: Compound
- **UniProt**: Protein
- **PubMed**: Publications

## Key Concepts

### Pipeline Lifecycle

```mermaid
sequenceDiagram
    participant CLI
    participant Runner
    participant Preflight
    participant Executor
    participant Postrun

    CLI->>Runner: run()
    Runner->>Preflight: execute()
    Preflight-->>Runner: health OK
    Runner->>Runner: acquire_lock()
    Runner->>Executor: execute()
    loop Each Batch
        Executor->>Executor: fetch → transform → write
    end
    Executor-->>Runner: done
    Runner->>Postrun: execute()
    Postrun-->>Runner: DQ + VACUUM done
    Runner->>Runner: release_lock()
    Runner-->>CLI: result
```

### Service Delegation Pattern

PipelineRunner delegates to specialized services:

| Service | Responsibility |
|---------|---------------|
| `PreflightService` | Health checks, lock acquisition |
| `PipelineExecutor` | Data flow orchestration |
| `PostrunService` | DQ validation, VACUUM |
| `MedallionLifecycleService` | Layer clearing policies |

## See Also

- [Core Components](application/core.md) - Detailed core component documentation
- [Services](application/services.md) - Application services reference
- [Transformers](application/transformers.md) - Transformer framework
- [Pipelines](application/pipelines.md) - Provider-specific pipelines
- [Domain Layer](domain.md) - Port interfaces used by application
