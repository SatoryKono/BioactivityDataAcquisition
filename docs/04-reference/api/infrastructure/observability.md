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

::: bioetl.infrastructure.observability.prometheus-metrics.PrometheusMetrics
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - observe-histogram
            - increment-counter
            - set-gauge
            - close

### NoOpMetrics

No-op implementation for testing or disabled metrics.
Located in `domain/ports/noop.py` (no I/O dependencies).

::: bioetl.domain.ports.noop.NoOpMetrics
    options:
        show-root-heading: true
        show-source: false

### Key Metrics

All metrics use `bioetl-` prefix. See [Metrics Contract](../../contracts/observability.md) for the full catalog.

| Metric | Type | Description |
|--------|------|-------------|
| `bioetl-pipeline-duration-seconds` | Histogram | Stage execution duration |
| `bioetl-records-processed-total` | Counter | Processed record count |
| `bioetl-errors-total` | Counter | Error count by type |
| `bioetl-batch-size-records` | Histogram | Batch size distribution |
| `bioetl-circuit-breaker-state` | Gauge | Circuit breaker status |
| `bioetl-dq-records-quarantined-total` | Counter | Quarantined records |

## Tracing

### OpenTelemetryTracer

OpenTelemetry tracing exporter.

::: bioetl.infrastructure.observability.tracing.OpenTelemetryTracer
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - get-tracer
            - close

### NoOpTracing

No-op implementation for testing or disabled tracing (default per ADR-022).
Located in `domain/ports/noop.py` (no I/O dependencies); re-exported via
`infrastructure.observability` for convenience.

::: bioetl.domain.ports.noop.NoOpTracing
    options:
        show-root-heading: true
        show-source: false

### Span Hierarchy

```
pipeline-run
├── preflight
│   ├── health-check-storage
│   ├── health-check-datasource
│   └── acquire-lock
├── execute
│   ├── batch-{batch-id}
│   │   ├── fetch
│   │   ├── transform
│   │   └── write
│   └── checkpoint
└── postrun
    ├── dq-check
    └── vacuum
```

## Logging

### create-logger

Factory function for creating structured loggers.

::: bioetl.infrastructure.observability.logging.create-logger
    options:
        show-root-heading: true
        show-source: false

### NoOpLogger

No-op implementation for testing.

::: bioetl.infrastructure.observability.noop-logger.NoOpLogger
    options:
        show-root-heading: true
        show-source: false

### Log Context

All logs include structured context per Log Schema (RULES.md §3.2.1):

```python
logger = logger.bind(
    run-id=str(run-id),
    pipeline="chembl-activity",
    stage="extract",
)

# Output:
# {"event": "batch-complete", "run-id": "abc-123", "pipeline": "chembl-activity", "stage": "extract", ...}
```

## Anomaly Detection

### DataQualityMonitor

Monitors metrics for anomalies in batch processing.

::: bioetl.infrastructure.observability.anomaly.monitor.DataQualityMonitor
    options:
        show-root-heading: true
        show-source: false

### Detection Algorithms

| Detector | Method | Use Case |
|----------|--------|----------|
| `ZScoreDetector` | Z-score | Normal distributions |
| `IQRDetector` | Interquartile range | Robust to outliers |
| `MADDetector` | Median absolute deviation | Non-normal data |

## Metrics Server

### start-metrics-server

HTTP server for Prometheus scraping.

::: bioetl.infrastructure.observability.server.start-metrics-server
    options:
        show-root-heading: true
        show-source: false

```python
# Start metrics server (default port: 8000)
start-metrics-server(port=8000)

# Prometheus can scrape at http://localhost:8000/metrics
```

## Usage Example

The recommended way to initialize the observability stack is via the bootstrap
functions in `composition/bootstrap/runtime/observability.py`:

```python
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap-observability-bundle,
)

# Initialize complete observability stack
bundle = bootstrap-observability-bundle(
    pipeline="chembl-activity",
    run-id=run-id,
    settings=settings,
)

# Use logger, metrics, tracer from the bundle
bundle.logger.info("batch-started", stage="extract", batch-id=str(batch-id))

bundle.metrics.increment-counter(
    "records-processed-total",
    records-count,
    {"pipeline": "chembl-activity", "stage": "extract", "run-type": "incremental"},
)
```

For manual initialization (e.g., tests):

```python
from bioetl.infrastructure.observability import PrometheusMetrics, OpenTelemetryTracer
from bioetl.infrastructure.observability.unified-logger import UnifiedLogger

metrics = PrometheusMetrics()
tracer = OpenTelemetryTracer(service-name="bioetl")
logger = UnifiedLogger(pipeline="chembl-activity", run-id=run-id)
```

## Configuration

Settings uses pydantic-settings with `env-prefix="BIOETL-"` and
`env-nested-delimiter="--"`. Nested observability settings map to
`BIOETL-OBSERVABILITY--<FIELD>` env vars.

### Top-level Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOETL-METRICS-PORT` | Prometheus HTTP server port | `8000` |
| `BIOETL-LOG-LEVEL` | Log level | `INFO` |
| `BIOETL-LOG-FORMAT` | Log format (`json` / `text`) | `json` |

### Nested Observability Variables (`BIOETL-OBSERVABILITY--*`)

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOETL-OBSERVABILITY--METRICS-ENABLED` | Enable metrics collection | `true` |
| `BIOETL-OBSERVABILITY--METRICS-SERVER-ENABLED` | Enable Prometheus HTTP server | `true` |
| `BIOETL-OBSERVABILITY--METRICS-FAIL-FAST` | Exit on server start failure | `false` |
| `BIOETL-OBSERVABILITY--METRICS-RETRY-COUNT` | Server start retry count (1–10) | `3` |
| `BIOETL-OBSERVABILITY--METRICS-RETRY-DELAY` | Retry delay in seconds (0.1–10) | `1.0` |
| `BIOETL-OBSERVABILITY--TRACING-ENABLED` | Enable OpenTelemetry tracing | `false` |
| `BIOETL-OBSERVABILITY--DQ-MONITOR-ENABLED` | Enable data quality monitor | `false` |
| `BIOETL-OBSERVABILITY--DQ-BASELINE-WINDOW` | Runs for baseline (1–30) | `7` |
| `BIOETL-OBSERVABILITY--DQ-Z-SCORE-THRESHOLD` | Anomaly z-score (1.5–5.0) | `2.5` |
| `BIOETL-OBSERVABILITY--DQ-MIN-BASELINE-SAMPLES` | Min samples before detection (1–10) | `3` |
| `BIOETL-OBSERVABILITY--DQ-COLD-START-RUNS` | Skip first N runs (0–20) | `5` |
| `BIOETL-OBSERVABILITY--DQ-ERROR-RATE-MAX` | Max error rate (0.0–1.0) | `0.10` |
| `BIOETL-OBSERVABILITY--DQ-QUALITY-SCORE-MIN` | Min quality score (0.0–1.0) | `0.80` |

## See Also

- [Domain Ports](../domain/ports.md) - MetricsPort, TracingPort, LoggerPort
- [Application Core](../application/core.md) - Pipeline observability
- [Storage Writers](storage.md) - Storage metrics
