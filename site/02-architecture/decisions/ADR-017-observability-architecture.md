# ADR-017: Observability Architecture

**Status:** Accepted
**Date:** 2025-12-26
**Decision makers:** @BioETL-Team

## Context

BioETL pipelines require comprehensive observability for debugging, performance monitoring, and operational alerting. The observability stack must follow the Ports & Adapters architecture to maintain testability and avoid infrastructure dependencies in domain/application layers.

## The Decision

We have implemented a **port-based observability architecture** with three formal Protocol definitions (`LoggerPort`, `MetricsPort`, `TracingPort`), Prometheus metrics with standardized labels, and NoOp implementations for testing.

### 1. Observability Ports as Formal Protocols

All observability concerns are abstracted through ports in `domain/ports/observability.py`:

```python
@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging."""
    def bind(self, **kwargs: Any) -> Self: ...
    def info(self, _event: str, **kwargs: Any) -> Any: ...
    def warning(self, _event: str, **kwargs: Any) -> Any: ...
    def error(self, _event: str, **kwargs: Any) -> Any: ...
    def debug(self, _event: str, **kwargs: Any) -> Any: ...
    def exception(self, _event: str, **kwargs: Any) -> Any: ...

@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""
    def observe_histogram(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None: ...
    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def close(self) -> None: ...

@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing (OpenTelemetry)."""
    def get_tracer(self, name: str) -> Any: ...
    def close(self) -> None: ...
```

### 2. Prometheus Metrics with Standardized Labels

Metrics are exposed at `http://localhost:{BIOETL_METRICS_PORT}/metrics` (default: 8000).

**Pipeline Metrics (prefix: `bioetl_`):**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Stage execution duration |
| `records_processed_total` | Counter | pipeline, stage, run_type | Processed record count |
| `errors_total` | Counter | pipeline, stage, error_code | Error count by type |
| `batch_size_records` | Histogram | pipeline, stage | Batch size distribution |

**Circuit Breaker Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `circuit_breaker_state` | Gauge | provider | 0=Closed, 1=Half-Open, 2=Open |
| `circuit_breaker_trips_total` | Counter | provider | Total OPEN transitions |
| `circuit_breaker_success_total` | Counter | provider | Successful requests |
| `circuit_breaker_failure_total` | Counter | provider | Failed requests |

**Data Quality Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `dq_records_quarantined_total` | Counter | pipeline, error_code | Quarantined records |
| `dq_anomaly_detected` | Counter | pipeline, metric, severity | Anomaly detections |
| `dq_baseline_samples` | Gauge | pipeline, metric | Baseline sample count |

**Maintenance Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `vacuum_duration_seconds` | Histogram | table | VACUUM operation time |
| `vacuum_files_removed_total` | Counter | table | Removed file count |
| `archive_duration_seconds` | Histogram | provider, entity | Archive operation time |

### 3. NoOp Implementations for Testing

Each port has a corresponding NoOp implementation in `infrastructure/observability/`:

| Port | NoOp Implementation | Purpose |
|------|---------------------|---------|
| `LoggerPort` | `NoOpLogger` | Silent logging for tests |
| `MetricsPort` | `NoOpMetrics` | Metric collection disabled |
| `TracingPort` | `NoOpTracing` | Tracing disabled |

**Key Features of NoOp Implementations:**
- Null Object Pattern: silently ignore all operations
- Idempotent: safe for repeated calls
- Warning on use (configurable): alerts developers in non-test environments
- Thread-safe: no shared mutable state

```python
# Testing: explicit opt-out, no warning
metrics = NoOpMetrics(warn_on_use=False)

# Production: warning if accidentally used
metrics = NoOpMetrics()  # Emits UserWarning
```

### 4. Log Schema

Structured JSON logs with mandatory fields:

| Field | Required | Example |
|-------|----------|---------|
| `ts` | MUST | `2025-12-26T10:00:00Z` |
| `level` | MUST | `INFO`, `ERROR` |
| `run_id` | MUST | UUID |
| `pipeline` | MUST | `chembl_activity` |
| `stage` | MUST | `extract`, `transform`, `load` |
| `dataset` | SHOULD | `chembl.activity` |
| `record_count` | SHOULD | 1000 |
| `error_type` | On errors | `SCHEMA_VIOLATION` |

## Justification

### 1. Ports Enable Clean Architecture

Application layer must not depend on infrastructure:
- `structlog` is never imported in `application/` or `interfaces/`
- All logging goes through `LoggerPort`
- Verified by architectural test `test_no_structlog_in_application_interfaces`

### 2. NoOp Pattern Simplifies Testing

Tests don't need to mock observability:
- Inject `NoOpLogger`, `NoOpMetrics`, `NoOpTracing`
- Zero overhead in test execution
- No side effects (file writes, network calls)

### 3. Standardized Labels Enable Aggregation

Consistent labeling across all metrics:
- `pipeline`: identifies the data pipeline
- `stage`: extract/transform/load phase
- `run_type`: incremental/backfill/rebuild
- Enables PromQL queries like: `sum(errors_total{pipeline="chembl_activity"}) by (error_code)`

### 4. Runtime Checkable Protocols

All ports use `@runtime_checkable`:
- Enables `isinstance()` checks at runtime
- Validates adapter implementations
- Tested by `tests/architecture/test_port_contracts.py`

## Implementation Details

### Port Location

```
src/bioetl/domain/ports/observability.py
    LoggerPort
    MetricsPort
    TracingPort
    DQMonitorPort
```

### Adapter Location

```
src/bioetl/infrastructure/observability/
    logging.py          # structlog adapter
    metrics.py          # Prometheus metric definitions
    prometheus_metrics.py # PrometheusMetrics adapter
    tracing.py          # OpenTelemetry adapter
    noop_logger.py      # NoOpLogger
    noop_metrics.py     # NoOpMetrics
    noop_tracing.py     # NoOpTracing
```

### Dependency Injection

```python
# composition/factories/observability.py
def create_metrics(config: Config) -> MetricsPort:
    if config.metrics_enabled:
        return PrometheusMetrics()
    return NoOpMetrics(warn_on_use=False)

def create_logger(config: Config) -> LoggerPort:
    if config.logging_enabled:
        return configure_structlog()
    return NoOpLogger()
```

### Usage in Pipeline

```python
# Application layer uses ports only
class PipelineRunner:
    def __init__(
        self,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort,
    ):
        self.logger = logger
        self.metrics = metrics
        self.tracing = tracing

    async def run_stage(self, stage: str) -> None:
        self.logger.info("stage_started", stage=stage)
        start = time.monotonic()

        # ... processing ...

        duration = time.monotonic() - start
        self.metrics.observe_histogram(
            "pipeline_duration_seconds",
            duration,
            {"pipeline": self.name, "stage": stage, "status": "success"},
        )
```

## Alternatives Considered

### 1. Direct structlog/Prometheus Usage

Rejected because:
- Violates layered architecture
- Tight coupling to infrastructure
- Difficult to test without mocks

### 2. Single Observability Port

Rejected because:
- Conflates separate concerns (logging, metrics, tracing)
- Some pipelines need only logging, not metrics
- Different lifecycle (metrics server vs log writes)

### 3. Mocking Instead of NoOp

Rejected because:
- `MagicMock` is heavier than NoOp objects
- No type safety on mock calls
- NoOp is cleaner Null Object Pattern

### 4. Global Logger/Metrics

Rejected because:
- Hides dependencies
- Difficult to test in isolation
- Violates dependency injection principle

## Consequences

### Positive

- **Clean architecture**: No infrastructure leakage into domain/application
- **Easy testing**: NoOp implementations require zero setup
- **Flexible backends**: Can swap Prometheus for CloudWatch, structlog for loguru
- **Type safety**: `@runtime_checkable` validates implementations
- **Consistent labels**: Standard aggregation patterns in dashboards

### Negative

- **Boilerplate**: Port + Adapter + NoOp for each concern
- **Indirection**: One level of abstraction vs direct calls
- **Learning curve**: Developers must use ports, not direct imports

## Related ADRs

- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports — initial decision for LoggerPort/MetricsPort
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes — logging constraints for reproducibility
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — metric integration
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — logging integration
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement — enforces this architecture
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — NoOp pattern for tracing defined here
