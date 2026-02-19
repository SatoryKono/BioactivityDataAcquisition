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

## Batch Transformation

### BatchTransformer

Streaming-режим интегрирован в BatchTransformer как streaming-processing mode.

Transforms batches of records from Bronze to Silver/Gold layers.

::: bioetl.application.core.batch-transformer.BatchTransformer
options:
show-root-heading: true
show-source: false

### TransformResult

Result of a transformation operation.

::: bioetl.application.core.batch-transformer.TransformResult
options:
show-root-heading: true
show-source: false

### TransformedRecord

Container for a transformed record with metadata.

::: bioetl.application.core.batch-transformer.TransformedRecord
options:
show-root-heading: true
show-source: false

## Batch Writing

### BatchWriter

Writes transformed batches to storage layers.

::: bioetl.application.core.batch-writer.BatchWriter
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

::: bioetl.application.core.memory-monitor.MemoryMonitor
options:
show-root-heading: true
show-source: false

### MemoryConfig

Memory monitoring configuration.

::: bioetl.application.core.memory-monitor.MemoryConfig
options:
show-root-heading: true
show-source: false

### MemoryStats

Memory usage statistics.

::: bioetl.application.core.memory-monitor.MemoryStats
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

## Medallion Lifecycle

### MedallionLifecycleService

Service for managing Medallion layer lifecycle operations.

::: bioetl.application.services.medallion-lifecycle.MedallionLifecycleService
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

## Transform Utilities

Utility functions for data transformation.

### normalize-string

::: bioetl.application.core.dict-transformers.normalize-string
options:
show-root-heading: true
show-source: false

### safe-extract

::: bioetl.application.core.dict-transformers.safe-extract
options:
show-root-heading: true
show-source: false

### flatten-nested-dict

::: bioetl.application.core.transform-utils.flatten-nested-dict
options:
show-root-heading: true
show-source: false

### extract-list-field

::: bioetl.application.core.transform-utils.extract-list-field
options:
show-root-heading: true
show-source: false

### aggregate-nested-lists

::: bioetl.application.core.transform-utils.aggregate-nested-lists
options:
show-root-heading: true
show-source: false

### parse-date-field

::: bioetl.application.core.dict-transformers.parse-date-field
options:
show-root-heading: true
show-source: false

### validate-smiles

::: bioetl.application.core.transform-utils.validate-smiles
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

## Medallion Types

### Layer

Enumeration for Medallion layers (BRONZE, SILVER, GOLD).

::: bioetl.domain.medallion.Layer
options:
show-root-heading: true
show-source: false

### WriteMode

Enumeration for write modes (MERGE, APPEND, OVERWRITE).

::: bioetl.domain.medallion.WriteMode
options:
show-root-heading: true
show-source: false

### WriteModePolicy

Policy for determining write mode based on run type and layer.

::: bioetl.domain.medallion.WriteModePolicy
options:
show-root-heading: true
show-source: false

## Usage Example

```python
from bioetl.application.core import (
    PipelineRunner,
    PipelineServices,
    CheckpointManager,
    PreflightService,
    BatchExecutor,
    BatchTransformer,
    BatchWriter,
    PipelineConfig,
    RuntimeConfig,
    WriteMode,
)

# Components are assembled in composition layer
# See: bioetl.composition.bootstrap.bootstrap-pipeline()
```

```python
# Transform utilities example
from bioetl.application.core import (
    normalize-string,
    safe-extract,
    parse-date-field,
    validate-smiles,
)

# Normalize strings for consistent comparison
name = normalize-string("  John Doe  ")  # "john doe"

# Safely extract nested values
value = safe-extract(data, "nested.path.to.value", default=None)

# Parse date strings
date = parse-date-field("2024-01-15", "%Y-%m-%d")

# Validate SMILES notation
is-valid = validate-smiles("CCO")  # True for ethanol
```

## See Also

- [Services](services.md) - Application services
- [Transformers](transformers.md) - Data transformation framework
- [Pipelines](pipelines.md) - Provider-specific pipelines
- [Bootstrap](../composition/bootstrap.md) - Component assembly
