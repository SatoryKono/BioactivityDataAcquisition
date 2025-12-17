# Interfaces Layer

Entry points and composition root.

## Purpose

Driving adapters that invoke the application layer. Contains CLI, Prefect integration, and factories (composition root).

## Modules

| Module | Type | Diagram |
|--------|------|---------|
| `cli.py` | handler | [overview.mmd](../../../docs/diagrams/interfaces/overview.mmd) |
| `bootstrap.py` | factory | [bootstrap.mmd](../../../docs/diagrams/interfaces/bootstrap.mmd) |
| `factories/chembl_activity.py` | factory | [overview.mmd](../../../docs/diagrams/interfaces/overview.mmd) |
| `orchestration/runner.py` | handler | [overview.mmd](../../../docs/diagrams/interfaces/overview.mmd) |
| `orchestration/signals.py` | handler | - |
| `orchestration/prefect/tasks.py` | handler | - |

## Dependencies

- Uses: `application`, `infrastructure`, `domain`
- Used by: External (CLI, Prefect)

## Key Components

### CLI (Click)
Entry point for pipeline execution:
```bash
bioetl run --pipeline chembl_activity --run-type incremental --resume
bioetl quarantine inspect --pipeline chembl_activity --limit 10
bioetl checkpoint list
```

### Bootstrap / Composition Root
`bootstrap_pipeline()` assembles all dependencies:
1. Create logger (structlog)
2. Get pipeline factory
3. Create PipelineServices with all adapters
4. Instantiate concrete pipeline

### Pipeline Factories
Create fully configured pipelines with dependency injection:
- `ChEMBLActivityPipelineFactory` - ChEMBL activity data

### Prefect Integration
Tasks for workflow orchestration:
- `execute_pipeline_task()` - Run single pipeline
- `run_pipeline_flow()` - Complete flow with checkpointing

### Signal Handlers
`setup_shutdown_handlers()` catches SIGTERM/SIGINT for graceful shutdown.
