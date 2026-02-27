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

::: bioetl.application.core.batch-executor.BatchExecutor
options:
show-root-heading: true
show-source: false
members:
\- --init--
\- execute
\- execute-batch

### BatchResult

Result of batch execution containing metrics and status.

::: bioetl.application.core.batch-executor.BatchResult
options:
show-root-heading: true
show-source: false

### RecordProcessor

Processes individual records through the transformation pipeline.

::: bioetl.application.core.record-processor.RecordProcessor
options:
show-root-heading: true
show-source: false

## Service Bundles

### PipelineServices

Bundle of common pipeline services injected via DI.

::: bioetl.application.core.pipeline-services.PipelineServices
options:
show-root-heading: true
show-source: false

## Infrastructure Services

### PreflightService

Pre-flight infrastructure validation before pipeline execution.

::: bioetl.application.core.preflight-service.PreflightService
options:
show-root-heading: true
show-source: false
members:
\- execute

### PostrunService

Post-run operations: DQ checks, VACUUM, cleanup.

::: bioetl.application.core.postrun-service.PostrunService
options:
show-root-heading: true
show-source: false
members:
\- execute

### PostrunResult

Result of post-run operations.

::: bioetl.application.core.postrun-service.PostrunResult
options:
show-root-heading: true
show-source: false

### DQResult

Data quality check result.

::: bioetl.application.core.postrun-service.DQResult
options:
show-root-heading: true
show-source: false

### DQEvaluationStatus

Enumeration for DQ evaluation status (PASSED, SOFT-FAIL, HARD-FAIL).

::: bioetl.application.core.postrun-service.DQEvaluationStatus
options:
show-root-heading: true
show-source: false

### VacuumResult

Result of VACUUM operation.

::: bioetl.application.core.postrun-service.VacuumResult
options:
show-root-heading: true
show-source: false

## State Management

### CheckpointManager

Pipeline checkpoint persistence for resume capability.

::: bioetl.application.core.checkpoint-manager.CheckpointManager
options:
show-root-heading: true
show-source: false
members:
\- save
\- load
\- delete

### LockManager

Distributed locking coordination.

::: bioetl.application.core.lock-manager.LockManager
options:
show-root-heading: true
show-source: false
members:
\- acquire
\- release

### QuarantineManager

Failed record quarantine management.

::: bioetl.application.core.quarantine-manager.QuarantineManager
options:
show-root-heading: true
show-source: false

## Memory Management

### MemoryMonitor

Memory usage monitoring for adaptive batch sizing.

::: bioetl.infrastructure.system.memory-monitor.MemoryMonitor
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

::: bioetl.application.core.shutdown.create-shutdown-service
options:
show-root-heading: true
show-source: false

## Cleanup Operations

### CleanupService

Cleanup operations for Bronze/Silver/Gold layers.

::: bioetl.application.core.cleanup-service.CleanupService
options:
show-root-heading: true
show-source: false

### CleanupResult

Result of cleanup operation.

::: bioetl.application.core.cleanup-service.CleanupResult
options:
show-root-heading: true
show-source: false

### CleanupPreview

Preview of files to be cleaned up.

::: bioetl.application.core.cleanup-service.CleanupPreview
options:
show-root-heading: true
show-source: false

### LayerInfo

Information about a storage layer.

::: bioetl.application.core.cleanup-service.LayerInfo
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

::: bioetl.application.services.medallion-types.ClearResult
options:
show-root-heading: true
show-source: false

### PrepareResult

Result of a layer prepare operation.

::: bioetl.application.services.medallion-types.PrepareResult
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
from bioetl.application.core.pipeline-services import PipelineServices
from bioetl.application.core.checkpoint-manager import CheckpointManager
from bioetl.application.core.preflight-service import PreflightService
from bioetl.application.core.batch-executor import BatchExecutor
from bioetl.domain.config import PipelineConfig, RuntimeConfig

# Components are assembled in composition layer
# See: bioetl.composition.bootstrap.bootstrap-pipeline()
```

```python
# Batch transformation and writing (see Transformers page)
from bioetl.application.core.batch-transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch-writer import BatchWriter

# Transform utilities (see Transformers page)
from bioetl.application.core.dict-transformers import (
    normalize-string,
    safe-extract,
    parse-date-field,
    validate-smiles,
)
```

## See Also

- [Services](services.md) - Application services
- [Transformers](transformers.md) - Data transformation framework
- [Pipelines](pipelines.md) - Provider-specific pipelines
- [Bootstrap](../composition/bootstrap.md) - Component assembly
