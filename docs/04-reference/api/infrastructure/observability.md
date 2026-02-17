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
Located in `domain/ports/noop.py` (no I/O dependencies).

::: bioetl.domain.ports.noop.NoOpMetrics
    options:
        show_root_heading: true
        show_source: false

### Key Metrics

All metrics use `bioetl_` prefix. See [Metrics Contract](../../contracts/observability.md) for the full catalog.

| Metric | Type | Description |
|--------|------|-------------|
| `bioetl_pipeline_duration_seconds` | Histogram | Stage execution duration |
| `bioetl_records_processed_total` | Counter | Processed record count |
| `bioetl_errors_total` | Counter | Error count by type |
| `bioetl_batch_size_records` | Histogram | Batch size distribution |
| `bioetl_circuit_breaker_state` | Gauge | Circuit breaker status |
| `bioetl_dq_records_quarantined_total` | Counter | Quarantined records |

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

No-op implementation for testing or disabled tracing (default per ADR-022).
Located in `domain/ports/noop.py` (no I/O dependencies); re-exported via
`infrastructure.observability` for convenience.

::: bioetl.domain.ports.noop.NoOpTracing
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

All logs include structured context per Log Schema (RULES.md §3.2.1):

```python
logger = logger.bind(
    run_id=str(run_id),
    pipeline="chembl_activity",
    stage="extract",
)

# Output:
# {"event": "batch_complete", "run_id": "abc-123", "pipeline": "chembl_activity", "stage": "extract", ...}
```

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
# Start metrics server (default port: 8000)
start_metrics_server(port=8000)

# Prometheus can scrape at http://localhost:8000/metrics
```

## Usage Example

The recommended way to initialize the observability stack is via the bootstrap
functions in `composition/bootstrap/runtime/observability.py`:

```python
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)

# Initialize complete observability stack
bundle = bootstrap_observability_bundle(
    pipeline="chembl_activity",
    run_id=run_id,
    settings=settings,
)

# Use logger, metrics, tracer from the bundle
bundle.logger.info("batch_started", stage="extract", batch_id=str(batch_id))

bundle.metrics.increment_counter(
    "records_processed_total",
    records_count,
    {"pipeline": "chembl_activity", "stage": "extract", "run_type": "incremental"},
)
```

For manual initialization (e.g., tests):

```python
from bioetl.infrastructure.observability import PrometheusMetrics, OpenTelemetryTracer
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

metrics = PrometheusMetrics()
tracer = OpenTelemetryTracer(service_name="bioetl")
logger = UnifiedLogger(pipeline="chembl_activity", run_id=run_id)
```

## Configuration

Settings uses pydantic-settings with `env_prefix="BIOETL_"` and
`env_nested_delimiter="__"`. Nested observability settings map to
`BIOETL_OBSERVABILITY__<FIELD>` env vars.

### Top-level Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOETL_METRICS_PORT` | Prometheus HTTP server port | `8000` |
| `BIOETL_LOG_LEVEL` | Log level | `INFO` |
| `BIOETL_LOG_FORMAT` | Log format (`json` / `text`) | `json` |

### Nested Observability Variables (`BIOETL_OBSERVABILITY__*`)

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOETL_OBSERVABILITY__METRICS_ENABLED` | Enable metrics collection | `true` |
| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | Enable Prometheus HTTP server | `true` |
| `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST` | Exit on server start failure | `false` |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_COUNT` | Server start retry count (1–10) | `3` |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_DELAY` | Retry delay in seconds (0.1–10) | `1.0` |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Enable OpenTelemetry tracing | `false` |
| `BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED` | Enable data quality monitor | `false` |
| `BIOETL_OBSERVABILITY__DQ_BASELINE_WINDOW` | Runs for baseline (1–30) | `7` |
| `BIOETL_OBSERVABILITY__DQ_Z_SCORE_THRESHOLD` | Anomaly z-score (1.5–5.0) | `2.5` |
| `BIOETL_OBSERVABILITY__DQ_MIN_BASELINE_SAMPLES` | Min samples before detection (1–10) | `3` |
| `BIOETL_OBSERVABILITY__DQ_COLD_START_RUNS` | Skip first N runs (0–20) | `5` |
| `BIOETL_OBSERVABILITY__DQ_ERROR_RATE_MAX` | Max error rate (0.0–1.0) | `0.10` |
| `BIOETL_OBSERVABILITY__DQ_QUALITY_SCORE_MIN` | Min quality score (0.0–1.0) | `0.80` |

## See Also

- [Domain Ports](../domain/ports.md) - MetricsPort, TracingPort, LoggerPort
- [Application Core](../application/core.md) - Pipeline observability
- [Storage Writers](storage.md) - Storage metrics
