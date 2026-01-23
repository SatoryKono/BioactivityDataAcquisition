# Observability

Metrics, tracing, and logging infrastructure.

## Overview

BioETL provides three observability pillars:

| Pillar | Implementation | Port |
|--------|---------------|------|
| **Metrics** | Prometheus | `MetricsPort` |
| **Tracing** | OpenTelemetry | `TracingPort` |
| **Logging** | structlog | `LoggerPort` |

## Metrics

### PrometheusMetrics

Prometheus-compatible metrics exporter.

::: bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - observe_histogram
            - increment_counter
            - set_gauge
            - close

### NoOpMetrics

No-op implementation for testing or disabled metrics.

::: bioetl.infrastructure.observability.noop_metrics.NoOpMetrics
    options:
        show_root_heading: true
        show_source: false

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `records_processed_total` | Counter | Total records processed |
| `batch_duration_seconds` | Histogram | Batch processing time |
| `dq_errors_total` | Counter | Data quality errors |
| `circuit_breaker_state` | Gauge | Circuit breaker status |
| `memory_usage_bytes` | Gauge | Current memory usage |

## Tracing

### OpenTelemetryTracer

OpenTelemetry tracing exporter.

::: bioetl.infrastructure.observability.tracing.OpenTelemetryTracer
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - get_tracer
            - close

### NoOpTracing

No-op implementation for testing or disabled tracing.

::: bioetl.infrastructure.observability.noop_tracing.NoOpTracing
    options:
        show_root_heading: true
        show_source: false

### Span Hierarchy

```
pipeline_run
├── preflight
│   ├── health_check_storage
│   ├── health_check_datasource
│   └── acquire_lock
├── execute
│   ├── batch_{batch_id}
│   │   ├── fetch
│   │   ├── transform
│   │   └── write
│   └── checkpoint
└── postrun
    ├── dq_check
    └── vacuum
```

## Logging

### create_logger

Factory function for creating structured loggers.

::: bioetl.infrastructure.observability.logging.create_logger
    options:
        show_root_heading: true
        show_source: false

### NoOpLogger

No-op implementation for testing.

::: bioetl.infrastructure.observability.noop_logger.NoOpLogger
    options:
        show_root_heading: true
        show_source: false

### Log Context

All logs include structured context:

```python
logger = logger.bind(
    run_id=str(run_id),
    pipeline_name="chembl_activity",
    entity_type="activity",
)

# Output:
# {"event": "batch_complete", "run_id": "abc-123", "pipeline_name": "chembl_activity", ...}
```

## Lineage Tracking

### LineageTracker

Data lineage tracking for audit and debugging.

::: bioetl.infrastructure.observability.lineage.LineageTracker
    options:
        show_root_heading: true
        show_source: false

## Anomaly Detection

### DataQualityMonitor

Monitors metrics for anomalies in batch processing.

::: bioetl.infrastructure.observability.anomaly.monitor.DataQualityMonitor
    options:
        show_root_heading: true
        show_source: false

### Detection Algorithms

| Detector | Method | Use Case |
|----------|--------|----------|
| `ZScoreDetector` | Z-score | Normal distributions |
| `IQRDetector` | Interquartile range | Robust to outliers |
| `MADDetector` | Median absolute deviation | Non-normal data |

## Metrics Server

### start_metrics_server

HTTP server for Prometheus scraping.

::: bioetl.infrastructure.observability.server.start_metrics_server
    options:
        show_root_heading: true
        show_source: false

```python
# Start metrics server
start_metrics_server(port=9090)

# Prometheus can scrape at http://localhost:9090/metrics
```

## Usage Example

```python
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer
from bioetl.infrastructure.observability.logging import create_logger

# Initialize observability stack
metrics = PrometheusMetrics()
tracer = OpenTelemetryTracer(service_name="bioetl-pipeline")
logger = create_logger(pipeline="chembl_activity", run_id=run_id)

# Use in pipeline
logger = logger.bind(run_id=str(run_id))

with tracer.get_tracer("bioetl").start_as_current_span("batch_processing") as span:
    span.set_attribute("batch_id", str(batch_id))

    # Process batch
    records_count = process_batch(records)

    # Record metrics
    metrics.increment_counter("records_processed_total", records_count, {"pipeline": "chembl_activity"})

    logger.info("batch_complete", records=records_count)
```

## Configuration

Environment variables for observability:

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOETL_METRICS_PORT` | Prometheus port | 9090 |
| `BIOETL_TRACING_ENDPOINT` | OTLP endpoint | None |
| `BIOETL_LOG_LEVEL` | Log level | INFO |
| `BIOETL_LOG_FORMAT` | Log format (json/console) | json |

## See Also

- [Domain Ports](../domain/ports.md) - MetricsPort, TracingPort, LoggerPort
- [Application Core](../application/core.md) - Pipeline observability
- [Storage Writers](storage.md) - Storage metrics
