# Application Core

Core pipeline execution infrastructure and services.

## Pipeline Execution

### PipelineRunner

Orchestrates pipeline execution lifecycle. Coordinates locking, checkpointing, and execution.

::: bioetl.application.core.runner.PipelineRunner
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - run
            - logger
            - services

### PipelineExecutor

Orchestrates data flow: extraction → transformation → writing.

::: bioetl.application.core.executor.PipelineExecutor
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - execute
            - batch_size
            - checkpoint_interval

### RecordProcessor

Processes individual records through the transformation pipeline.

::: bioetl.application.core.record_processor.RecordProcessor
    options:
        show_root_heading: true
        show_source: false

## Service Bundles

### PipelineServices

Bundle of common pipeline services injected via DI.

::: bioetl.application.core.pipeline_services.PipelineServices
    options:
        show_root_heading: true
        show_source: false

### RunnerServices

Bundle of application services for PipelineRunner.

::: bioetl.application.core.runner_services.RunnerServices
    options:
        show_root_heading: true
        show_source: false

## Infrastructure Services

### PreflightService

Pre-flight infrastructure validation before pipeline execution.

::: bioetl.application.core.preflight_service.PreflightService
    options:
        show_root_heading: true
        show_source: false
        members:
            - execute

### PostrunService

Post-run operations: DQ checks, VACUUM, cleanup.

::: bioetl.application.core.postrun_service.PostrunService
    options:
        show_root_heading: true
        show_source: false
        members:
            - execute

### LifecycleOrchestrator

Medallion layer clearing policy orchestration.

::: bioetl.application.core.lifecycle_orchestrator.LifecycleOrchestrator
    options:
        show_root_heading: true
        show_source: false

### ClearDecision

Decision result for layer clearing.

::: bioetl.application.core.lifecycle_orchestrator.ClearDecision
    options:
        show_root_heading: true
        show_source: false

## State Management

### CheckpointManager

Pipeline checkpoint persistence for resume capability.

::: bioetl.application.core.checkpoint_manager.CheckpointManager
    options:
        show_root_heading: true
        show_source: false
        members:
            - save
            - load
            - delete

### LockManager

Distributed locking coordination.

::: bioetl.application.core.lock_manager.LockManager
    options:
        show_root_heading: true
        show_source: false
        members:
            - acquire
            - release

### QuarantineManager

Failed record quarantine management.

::: bioetl.application.core.quarantine_manager.QuarantineManager
    options:
        show_root_heading: true
        show_source: false

## Memory Management

### MemoryMonitor

Memory usage monitoring for adaptive batch sizing.

::: bioetl.application.core.memory_monitor.MemoryMonitor
    options:
        show_root_heading: true
        show_source: false

### MemoryConfig

Memory monitoring configuration.

::: bioetl.application.core.memory_monitor.MemoryConfig
    options:
        show_root_heading: true
        show_source: false

### MemoryStats

Memory usage statistics.

::: bioetl.application.core.memory_monitor.MemoryStats
    options:
        show_root_heading: true
        show_source: false

## Medallion Policy

### WriteModePolicy

Write mode policy for different run types.

::: bioetl.application.core.medallion_policy.WriteModePolicy
    options:
        show_root_heading: true
        show_source: false

### WriteMode

Silver layer write strategy enum.

::: bioetl.application.core.medallion_policy.WriteMode
    options:
        show_root_heading: true
        show_source: false

### Layer

Medallion layer enum.

::: bioetl.application.core.medallion_policy.Layer
    options:
        show_root_heading: true
        show_source: false

## Health Monitoring

### HealthAggregator

Aggregates health status from multiple components.

::: bioetl.application.core.health_aggregator.HealthAggregator
    options:
        show_root_heading: true
        show_source: false

## Shutdown Handling

### ShutdownSignal

Graceful shutdown signal handler.

::: bioetl.application.core.shutdown.ShutdownSignal
    options:
        show_root_heading: true
        show_source: false

### PipelineShutdownError

Raised when pipeline receives shutdown signal.

::: bioetl.application.core.shutdown.PipelineShutdownError
    options:
        show_root_heading: true
        show_source: false

## Cleanup Operations

### CleanupService

Cleanup operations for Bronze/Silver/Gold layers.

::: bioetl.application.core.cleanup_service.CleanupService
    options:
        show_root_heading: true
        show_source: false

### CleanupResult

Result of cleanup operation.

::: bioetl.application.core.cleanup_service.CleanupResult
    options:
        show_root_heading: true
        show_source: false

### CleanupPreview

Preview of files to be cleaned up.

::: bioetl.application.core.cleanup_service.CleanupPreview
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.application.core import (
    PipelineRunner,
    PipelineServices,
    CheckpointManager,
    PreflightService,
)

# Components are assembled in composition layer
# See: bioetl.composition.bootstrap.bootstrap_pipeline()

# Example: Direct executor usage
# executor = PipelineExecutor(
#     services=pipeline_services,
#     record_processor=processor,
#     checkpoint_manager=checkpoint_manager,
#     shutdown_signal=shutdown_signal,
#     entity_type="activity",
#     batch_size=100,
# )

# Execute data flow
# await executor.execute()
```

## See Also

- [Transformers](transformers.md) - Data transformation framework
- [Pipelines](pipelines.md) - Provider-specific pipelines
- [Bootstrap](../composition/bootstrap.md) - Component assembly
