# Application Layer

Business logic and pipeline orchestration.

## Purpose

Coordinates domain logic and infrastructure adapters. Contains pipeline execution flow, managers for cross-cutting concerns.

## Modules

| Module | Type | Diagram |
|--------|------|---------|
| `core/base.py` | service | [base.mmd](../../../docs/diagrams/application/core/base.mmd) |
| `core/orchestrator.py` | service | [orchestrator.mmd](../../../docs/diagrams/application/core/orchestrator.mmd) |
| `core/executor.py` | service | [executor.mmd](../../../docs/diagrams/application/core/executor.mmd) |
| `core/record_processor.py` | service | [record_processor.mmd](../../../docs/diagrams/application/core/record_processor.mmd) |
| `core/lock_manager.py` | service | [lock_manager.mmd](../../../docs/diagrams/application/core/lock_manager.mmd) |
| `core/checkpoint_manager.py` | service | [managers.mmd](../../../docs/diagrams/application/core/managers.mmd) |
| `core/quarantine_manager.py` | service | [managers.mmd](../../../docs/diagrams/application/core/managers.mmd) |
| `core/shutdown.py` | util | [shutdown.mmd](../../../docs/diagrams/application/core/shutdown.mmd) |
| `core/pipeline_config.py` | config | - |
| `core/pipeline_services.py` | dto | - |
| `pipelines/chembl_activity.py` | pipeline | [chembl_activity.mmd](../../../docs/diagrams/application/pipelines/chembl_activity.mmd) |

## Dependencies

- Uses: `domain` (ports, types, exceptions)
- Used by: `interfaces`

## Key Components

### BasePipeline (Abstract)
Base class for all ETL pipelines. Constructor accepts 3 parameters per ADR-0005:
- `config: PipelineConfig` - Static configuration
- `runtime: PipelineRuntimeConfig` - Runtime parameters
- `services: PipelineServices` - Injected dependencies

### PipelineOrchestrator
Manages pipeline lifecycle:
1. Setup signal handlers
2. Acquire distributed lock
3. Load checkpoint
4. Execute batches
5. Save checkpoint
6. Release lock

### PipelineExecutor
Executes data flow:
1. Fetch from DataSource
2. Write Bronze
3. Transform → Silver
4. Filter → Gold
5. Handle errors → Quarantine

### Managers
- `CheckpointManager` - Watermark persistence
- `LockManager` - Distributed lock with heartbeat
- `QuarantineManager` - Failed records handling
