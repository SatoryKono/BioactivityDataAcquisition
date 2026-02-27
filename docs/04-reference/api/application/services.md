# Application Services

Specialized services that encapsulate business logic and orchestration rules. These services are typically injected into the PipelineRunner or used by other application components.

## Medallion Lifecycle

### MedallionLifecycleService

Orchestrates the lifecycle of Medallion layers, including clearing data before runs and managing retention.

::: bioetl.application.services.medallion-lifecycle.MedallionLifecycleService
    options:
        show-root-heading: true
        show-source: false

### VacuumService

Manages Delta Lake VACUUM operations to remove old files.

::: bioetl.application.services.vacuum-service.VacuumService
    options:
        show-root-heading: true
        show-source: false

### BronzeCleanupService

Manages cleanup of Bronze layer files (JSONL) based on retention policies.

::: bioetl.application.services.bronze-cleanup-service.BronzeCleanupService
    options:
        show-root-heading: true
        show-source: false

## Data Quality & Reporting

### DataQualityService

Orchestrates data quality checks and validation.

::: bioetl.application.services.data-quality-service.DataQualityService
    options:
        show-root-heading: true
        show-source: false

### DQReportService

Generates and persists data quality reports.

::: bioetl.application.services.dq-report-service.DQReportService
    options:
        show-root-heading: true
        show-source: false

### DQMetricsCalculator

Calculates aggregated DQ metrics from raw validation results.

::: bioetl.domain.services.dq-metrics-calculator.DQMetricsCalculator
    options:
        show-root-heading: true
        show-source: false

## Infrastructure Management

### LockService

Manages distributed locks for pipeline coordination.

::: bioetl.application.services.lock-service.LockService
    options:
        show-root-heading: true
        show-source: false

### CheckpointService

Manages pipeline state persistence and recovery.

::: bioetl.application.services.checkpoint-service.CheckpointService
    options:
        show-root-heading: true
        show-source: false

### QuarantineService

Manages failed records and quarantine operations.

::: bioetl.application.services.quarantine-service.QuarantineService
    options:
        show-root-heading: true
        show-source: false

### ShutdownService

Coordinates graceful shutdown of pipeline components.

::: bioetl.application.services.shutdown-service.ShutdownService
    options:
        show-root-heading: true
        show-source: false

### ConfigService

Manages configuration loading and validation.

::: bioetl.application.services.config-service.ConfigService
    options:
        show-root-heading: true
        show-source: false

## Observability & Health

### HealthService

Aggregates health status from multiple components.

::: bioetl.application.services.health-service.HealthService
    options:
        show-root-heading: true
        show-source: false

### MetricsService

Manages application-level metrics collection.

::: bioetl.application.services.metrics-service.MetricsService
    options:
        show-root-heading: true
        show-source: false

## Data Export

### ExportService

Manages data export operations (e.g., to CSV/Parquet).

::: bioetl.application.services.export-service.ExportService
    options:
        show-root-heading: true
        show-source: false

## Orchestration

### PipelineRunnerService

Higher-level service for managing multiple pipeline runners.

::: bioetl.application.services.pipeline-runner-service.PipelineRunnerService
    options:
        show-root-heading: true
        show-source: false
