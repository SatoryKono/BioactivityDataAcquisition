# Application Core

Core pipeline execution infrastructure and services.

## Pipeline Execution

### PipelineRunner

Orchestrates pipeline execution lifecycle. Coordinates locking, checkpointing, and execution.

::: bioetl.application.core.runner.PipelineRunner
options:
show-root-heading: true
show-source: false
members:
\- --init--
\- run
\- logger
\- services

### BasePipeline

Abstract base class for all ETL pipelines. Provides template method pattern for pipeline configuration.

::: bioetl.application.core.base.BasePipeline
options:
show-root-heading: true
show-source: false

### BatchExecutor

Unified batch executor for ETL pipeline orchestration. Handles extraction → transformation → writing flow with adaptive batch sizing.

::: bioetl.application.core.batch_executor.BatchExecutor
options:
show-root-heading: true
show-source: false
members:
\- --init--
\- execute
\- execute-batch

### BatchResult

Result of batch execution containing metrics and status.

::: bioetl.application.core.batch_executor.BatchResult
options:
show-root-heading: true
show-source: false

### RecordProcessor

Processes individual records through the transformation pipeline.

::: bioetl.application.core.record_processor.RecordProcessor
options:
show-root-heading: true
show-source: false

## Service Bundles

### PipelineServices

Bundle of common pipeline services injected via DI.

::: bioetl.application.core.pipeline_services.PipelineServices
options:
show-root-heading: true
show-source: false

## Infrastructure Services

### PreflightService

Pre-flight infrastructure validation before pipeline execution.

::: bioetl.application.core.preflight_service.PreflightService
options:
show-root-heading: true
show-source: false
members:
\- execute

### PostrunService

Post-run operations: DQ checks, VACUUM, cleanup.

::: bioetl.application.core.postrun_service.PostrunService
options:
show-root-heading: true
show-source: false
members:
\- execute

### PostrunResult

Result of post-run operations.

::: bioetl.application.core.postrun_service.PostrunResult
options:
show-root-heading: true
show-source: false

### DQResult

Data quality check result.

::: bioetl.application.core.postrun_service.DQResult
options:
show-root-heading: true
show-source: false

### DQEvaluationStatus

Enumeration for DQ evaluation status (PASSED, SOFT-FAIL, HARD-FAIL).

::: bioetl.application.core.postrun_service.DQEvaluationStatus
options:
show-root-heading: true
show-source: false

### VacuumResult

Result of VACUUM operation.

::: bioetl.application.core.postrun_service.VacuumResult
options:
show-root-heading: true
show-source: false

## State Management

### CheckpointManager

Pipeline checkpoint persistence for resume capability.

::: bioetl.application.core.checkpoint_manager.CheckpointManager
options:
show-root-heading: true
show-source: false
members:
\- save
\- load
\- delete

### LockManager

Distributed locking coordination.

::: bioetl.application.core.lock_manager.LockManager
options:
show-root-heading: true
show-source: false
members:
\- acquire
\- release

### QuarantineManager

Failed record quarantine management.

::: bioetl.application.core.quarantine_manager.QuarantineManager
options:
show-root-heading: true
show-source: false

## Memory Management

### MemoryMonitor

Memory usage monitoring for adaptive batch sizing.

::: bioetl.infrastructure.system.memory_monitor.MemoryMonitor
options:
show-root-heading: true
show-source: false

### MemoryConfig

Memory monitoring configuration.

::: bioetl.domain.config.memory.MemoryConfig
options:
show-root-heading: true
show-source: false

### MemoryStats

Memory usage statistics.

::: bioetl.domain.ports.memory.MemoryStats
options:
show-root-heading: true
show-source: false

## Shutdown Handling

### ShutdownSignal

Graceful shutdown signal handler.

::: bioetl.application.core.shutdown.ShutdownSignal
options:
show-root-heading: true
show-source: false

### ShutdownService

Service for coordinating graceful shutdown.

::: bioetl.application.core.shutdown.ShutdownService
options:
show-root-heading: true
show-source: false

### ShutdownReason

Enumeration for shutdown reasons.

::: bioetl.application.core.shutdown.ShutdownReason
options:
show-root-heading: true
show-source: false

### PipelineShutdownError

Raised when pipeline receives shutdown signal.

::: bioetl.application.core.shutdown.PipelineShutdownError
options:
show-root-heading: true
show-source: false

### create-shutdown-service

Factory function for creating shutdown service.

::: bioetl.application.core.shutdown.create_shutdown_service
options:
show-root-heading: true
show-source: false

## Cleanup Operations

### CleanupService

Cleanup operations for Bronze/Silver/Gold layers.

::: bioetl.application.core.cleanup_service.CleanupService
options:
show-root-heading: true
show-source: false

### CleanupResult

Result of cleanup operation.

::: bioetl.application.core.cleanup_service.CleanupResult
options:
show-root-heading: true
show-source: false

### CleanupPreview

Preview of files to be cleaned up.

::: bioetl.application.core.cleanup_service.CleanupPreview
options:
show-root-heading: true
show-source: false

### LayerInfo

Information about a storage layer.

::: bioetl.application.core.cleanup_service.LayerInfo
options:
show-root-heading: true
show-source: false

## Medallion Types

### Layer

Enumeration for Medallion layers (BRONZE, SILVER, GOLD).

::: bioetl.domain.medallion.Layer
options:
show-root-heading: true
show-source: false

### WriteModePolicy

Policy for determining write mode based on run type and layer.

::: bioetl.domain.medallion.WriteModePolicy
options:
show-root-heading: true
show-source: false

### ClearResult

Result of a layer clear operation.

::: bioetl.application.services.medallion_types.ClearResult
options:
show-root-heading: true
show-source: false

### PrepareResult

Result of a layer prepare operation.

::: bioetl.application.services.medallion_types.PrepareResult
options:
show-root-heading: true
show-source: false

## Configuration

### PipelineConfig

Static pipeline configuration loaded from YAML.

::: bioetl.domain.config.PipelineConfig
options:
show-root-heading: true
show-source: false

### RuntimeConfig

Runtime configuration from CLI/environment.

::: bioetl.domain.config.RuntimeConfig
options:
show-root-heading: true
show-source: false

## Usage Example

```python
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.domain.config import PipelineConfig, RuntimeConfig

# Components are assembled in composition layer
# See: bioetl.composition.bootstrap.bootstrap_pipeline()
```

```python
# Batch transformation and writing (see Transformers page)
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter

# Transform utilities (see Transformers page)
from bioetl.application.core.dict_transformers import (
    normalize_string,
    safe_extract,
    parse_date_field,
    validate_smiles,
)
```

## See Also

- [Services](services.md) - Application services
- [Transformers](transformers.md) - Data transformation framework
- [Pipelines](pipelines.md) - Provider-specific pipelines
- [Bootstrap](../composition/bootstrap.md) - Component assembly
