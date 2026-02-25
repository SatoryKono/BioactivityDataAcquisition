# Application Services

Specialized services that encapsulate business logic and orchestration rules. These services are typically injected into the PipelineRunner or used by other application components.

## Medallion Lifecycle

### MedallionLifecycleService

Orchestrates the lifecycle of Medallion layers, including clearing data before runs and managing retention.

::: bioetl.application.services.medallion_lifecycle.MedallionLifecycleService
    options:
        show_root_heading: true
        show_source: false

### VacuumService

Manages Delta Lake VACUUM operations to remove old files.

::: bioetl.application.services.vacuum_service.VacuumService
    options:
        show_root_heading: true
        show_source: false

### BronzeCleanupService

Manages cleanup of Bronze layer files (JSONL) based on retention policies.

::: bioetl.application.services.bronze_cleanup_service.BronzeCleanupService
    options:
        show_root_heading: true
        show_source: false

## Data Quality & Reporting

### DataQualityService

Orchestrates data quality checks and validation.

::: bioetl.application.services.data_quality_service.DataQualityService
    options:
        show_root_heading: true
        show_source: false

### DQReportService

Generates and persists data quality reports.

::: bioetl.application.services.dq_report_service.DQReportService
    options:
        show_root_heading: true
        show_source: false

### DQMetricsCalculator

Calculates aggregated DQ metrics from raw validation results.

::: bioetl.domain.services.dq_metrics_calculator.DQMetricsCalculator
    options:
        show_root_heading: true
        show_source: false

## Infrastructure Management

### LockService

Manages distributed locks for pipeline coordination.

::: bioetl.application.services.lock_service.LockService
    options:
        show_root_heading: true
        show_source: false

### CheckpointService

Manages pipeline state persistence and recovery.

::: bioetl.application.services.checkpoint_service.CheckpointService
    options:
        show_root_heading: true
        show_source: false

### QuarantineService

Manages failed records and quarantine operations.

::: bioetl.application.services.quarantine_service.QuarantineService
    options:
        show_root_heading: true
        show_source: false

### ShutdownService

Coordinates graceful shutdown of pipeline components.

::: bioetl.application.services.shutdown_service.ShutdownService
    options:
        show_root_heading: true
        show_source: false

### ConfigService

Manages configuration loading and validation.

::: bioetl.application.services.config_service.ConfigService
    options:
        show_root_heading: true
        show_source: false

## Observability & Health

### HealthService

Aggregates health status from multiple components.

::: bioetl.application.services.health_service.HealthService
    options:
        show_root_heading: true
        show_source: false

### MetricsService

Manages application-level metrics collection.

::: bioetl.application.services.metrics_service.MetricsService
    options:
        show_root_heading: true
        show_source: false

## Data Export

### ExportService

Manages data export operations (e.g., to CSV/Parquet).

::: bioetl.application.services.export_service.ExportService
    options:
        show_root_heading: true
        show_source: false

## Orchestration

### PipelineRunnerService

Higher-level service for managing multiple pipeline runners.

::: bioetl.application.services.pipeline_runner_service.PipelineRunnerService
    options:
        show_root_heading: true
        show_source: false
