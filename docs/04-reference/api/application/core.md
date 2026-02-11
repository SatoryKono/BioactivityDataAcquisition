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
\- __init__
\- run
\- logger
\- services

### BasePipeline

Abstract base class for all ETL pipelines. Provides template method pattern for pipeline configuration.

::: bioetl.application.core.base.BasePipeline
options:
show_root_heading: true
show_source: false

### BatchExecutor

Unified batch executor for ETL pipeline orchestration. Handles extraction → transformation → writing flow with adaptive batch sizing.

::: bioetl.application.core.batch_executor.BatchExecutor
options:
show_root_heading: true
show_source: false
members:
\- __init__
\- execute
\- execute_batch

### BatchResult

Result of batch execution containing metrics and status.

::: bioetl.application.core.batch_executor.BatchResult
options:
show_root_heading: true
show_source: false

### RecordProcessor

Processes individual records through the transformation pipeline.

::: bioetl.application.core.record_processor.RecordProcessor
options:
show_root_heading: true
show_source: false

## Batch Transformation

### BatchTransformer

Transforms batches of records from Bronze to Silver/Gold layers.

::: bioetl.application.core.batch_transformer.BatchTransformer
options:
show_root_heading: true
show_source: false

### 

Streaming processor for large batches with memory management.

::: bioetl.application.core.batch_transformer.
options:
show_root_heading: true
show_source: false

### TransformResult

Result of a transformation operation.

::: bioetl.application.core.batch_transformer.TransformResult
options:
show_root_heading: true
show_source: false

### TransformedRecord

Container for a transformed record with metadata.

::: bioetl.application.core.batch_transformer.TransformedRecord
options:
show_root_heading: true
show_source: false

## Batch Writing

### BatchWriter

Writes transformed batches to storage layers.

::: bioetl.application.core.batch_writer.BatchWriter
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

## Infrastructure Services

### PreflightService

Pre-flight infrastructure validation before pipeline execution.

::: bioetl.application.core.preflight_service.PreflightService
options:
show_root_heading: true
show_source: false
members:
\- execute

### PostrunService

Post-run operations: DQ checks, VACUUM, cleanup.

::: bioetl.application.core.postrun_service.PostrunService
options:
show_root_heading: true
show_source: false
members:
\- execute

### PostrunResult

Result of post-run operations.

::: bioetl.application.core.postrun_service.PostrunResult
options:
show_root_heading: true
show_source: false

### DQResult

Data quality check result.

::: bioetl.application.core.postrun_service.DQResult
options:
show_root_heading: true
show_source: false

### DQEvaluationStatus

Enumeration for DQ evaluation status (PASSED, SOFT_FAIL, HARD_FAIL).

::: bioetl.application.core.postrun_service.DQEvaluationStatus
options:
show_root_heading: true
show_source: false

### VacuumResult

Result of VACUUM operation.

::: bioetl.application.core.postrun_service.VacuumResult
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
\- save
\- load
\- delete

### LockManager

Distributed locking coordination.

::: bioetl.application.core.lock_manager.LockManager
options:
show_root_heading: true
show_source: false
members:
\- acquire
\- release

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

## Shutdown Handling

### ShutdownSignal

Graceful shutdown signal handler.

::: bioetl.application.core.shutdown.ShutdownSignal
options:
show_root_heading: true
show_source: false

### ShutdownService

Service for coordinating graceful shutdown.

::: bioetl.application.core.shutdown.ShutdownService
options:
show_root_heading: true
show_source: false

### ShutdownReason

Enumeration for shutdown reasons.

::: bioetl.application.core.shutdown.ShutdownReason
options:
show_root_heading: true
show_source: false

### PipelineShutdownError

Raised when pipeline receives shutdown signal.

::: bioetl.application.core.shutdown.PipelineShutdownError
options:
show_root_heading: true
show_source: false

### create_shutdown_service

Factory function for creating shutdown service.

::: bioetl.application.core.shutdown.create_shutdown_service
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

### LayerInfo

Information about a storage layer.

::: bioetl.application.core.cleanup_service.LayerInfo
options:
show_root_heading: true
show_source: false

## Medallion Lifecycle

### MedallionLifecycleService

Service for managing Medallion layer lifecycle operations.

::: bioetl.application.services.medallion_lifecycle.MedallionLifecycleService
options:
show_root_heading: true
show_source: false

### ClearResult

Result of a layer clear operation.

::: bioetl.application.services.medallion_types.ClearResult
options:
show_root_heading: true
show_source: false

### PrepareResult

Result of a layer prepare operation.

::: bioetl.application.services.medallion_types.PrepareResult
options:
show_root_heading: true
show_source: false

## Transform Utilities

Utility functions for data transformation.

### normalize_string

::: bioetl.application.core.dict_transformers.normalize_string
options:
show_root_heading: true
show_source: false

### safe_extract

::: bioetl.application.core.dict_transformers.safe_extract
options:
show_root_heading: true
show_source: false

### flatten_nested_dict

::: bioetl.application.core.dict_transformers.flatten_nested_dict
options:
show_root_heading: true
show_source: false

### extract_list_field

::: bioetl.application.core.dict_transformers.extract_list_field
options:
show_root_heading: true
show_source: false

### aggregate_nested_lists

::: bioetl.application.core.dict_transformers.aggregate_nested_lists
options:
show_root_heading: true
show_source: false

### parse_date_field

::: bioetl.application.core.dict_transformers.parse_date_field
options:
show_root_heading: true
show_source: false

### validate_smiles

::: bioetl.application.core.dict_transformers.validate_smiles
options:
show_root_heading: true
show_source: false

## Configuration

### PipelineConfig

Static pipeline configuration loaded from YAML.

::: bioetl.domain.config.PipelineConfig
options:
show_root_heading: true
show_source: false

### RuntimeConfig

Runtime configuration from CLI/environment.

::: bioetl.domain.config.RuntimeConfig
options:
show_root_heading: true
show_source: false

## Medallion Types

### Layer

Enumeration for Medallion layers (BRONZE, SILVER, GOLD).

::: bioetl.domain.medallion.Layer
options:
show_root_heading: true
show_source: false

### WriteMode

Enumeration for write modes (MERGE, APPEND, OVERWRITE).

::: bioetl.domain.medallion.WriteMode
options:
show_root_heading: true
show_source: false

### WriteModePolicy

Policy for determining write mode based on run type and layer.

::: bioetl.domain.medallion.WriteModePolicy
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
    BatchExecutor,
    BatchTransformer,
    BatchWriter,
    PipelineConfig,
    RuntimeConfig,
    WriteMode,
)

# Components are assembled in composition layer
# See: bioetl.composition.bootstrap.bootstrap_pipeline()
```

```python
# Transform utilities example
from bioetl.application.core import (
    normalize_string,
    safe_extract,
    parse_date_field,
    validate_smiles,
)

# Normalize strings for consistent comparison
name = normalize_string("  John Doe  ")  # "john doe"

# Safely extract nested values
value = safe_extract(data, "nested.path.to.value", default=None)

# Parse date strings
date = parse_date_field("2024-01-15", "%Y-%m-%d")

# Validate SMILES notation
is_valid = validate_smiles("CCO")  # True for ethanol
```

## See Also

- [Services](services.md) - Application services
- [Transformers](transformers.md) - Data transformation framework
- [Pipelines](pipelines.md) - Provider-specific pipelines
- [Bootstrap](../composition/bootstrap.md) - Component assembly

Streaming-режим интегрирован в BatchTransformer как streaming_processing mode.
