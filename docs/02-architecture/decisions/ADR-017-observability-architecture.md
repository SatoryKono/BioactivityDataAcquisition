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
@runtime-checkable
class LoggerPort(Protocol):
    """Port for structured logging."""
    def bind(self, **kwargs: Any) -> Self: ...
    def info(self, -event: str, **kwargs: Any) -> Any: ...
    def warning(self, -event: str, **kwargs: Any) -> Any: ...
    def error(self, -event: str, **kwargs: Any) -> Any: ...
    def debug(self, -event: str, **kwargs: Any) -> Any: ...
    def exception(self, -event: str, **kwargs: Any) -> Any: ...

@runtime-checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""
    def observe-histogram(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def increment-counter(self, name: str, value: int, labels: dict[str, str]) -> None: ...
    def set-gauge(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def close(self) -> None: ...

@runtime-checkable
class TracingPort(Protocol):
    """Port for distributed tracing — an OpenTelemetry Tracing API facade.

    Deliberately modeled after the OTel API: get-tracer() returns an
    OTel-compatible Tracer (start-as-current-span, Span context manager).
    This is an intentional design choice — see ADR-022 for the rationale.
    """
    def get-tracer(self, name: str) -> Any: ...
    def close(self) -> None: ...
```

### 2. Prometheus Metrics with Standardized Labels

Metrics are exposed at `http://localhost:{BIOETL-METRICS-PORT}/metrics` (default: 8000).

**Pipeline Metrics (prefix: `bioetl-`):**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `pipeline-duration-seconds` | Histogram | pipeline, stage, status, run-type | Stage execution duration |
| `records-processed-total` | Counter | pipeline, stage, run-type | Processed record count |
| `errors-total` | Counter | pipeline, stage, error-code | Error count by type |
| `batch-size-records` | Histogram | pipeline, stage | Batch size distribution |

**Circuit Breaker Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `circuit-breaker-state` | Gauge | adapter | 0=Closed, 1=Half-Open, 2=Open |
| `circuit-breaker-trips-total` | Counter | adapter | Total OPEN transitions |
| `circuit-breaker-success-total` | Counter | adapter | Successful calls |
| `circuit-breaker-failure-total` | Counter | adapter | Failed calls |

**Data Quality Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `dq-records-quarantined-total` | Counter | pipeline, error-code | Quarantined records |
| `dq-anomaly-detected` | Counter | pipeline, metric, severity | Anomaly detections |
| `dq-baseline-samples` | Gauge | pipeline, metric | Baseline sample count |

**Maintenance Metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `vacuum-duration-seconds` | Histogram | table | VACUUM operation time |
| `vacuum-files-removed-total` | Counter | table, layer | Removed file count |
| `archive-duration-seconds` | Histogram | table | Archive operation time |

### 3. NoOp Implementations for Testing

Each port has a corresponding NoOp implementation. `NoOpMetrics` and `NoOpTracing`
live in `domain/ports/noop.py` (no I/O dependencies), while `NoOpLogger` lives in
`infrastructure/observability/noop-logger.py` (adapter-level fallback):

| Port | NoOp Implementation | Location |
|------|---------------------|----------|
| `LoggerPort` | `NoOpLogger` | `infrastructure/observability/noop-logger.py` |
| `MetricsPort` | `NoOpMetrics` | `domain/ports/noop.py` |
| `TracingPort` | `NoOpTracing` | `domain/ports/noop.py` (mirrors OTel API surface) |

**Key Features of NoOp Implementations:**
- Null Object Pattern: silently ignore all operations
- Idempotent: safe for repeated calls
- Warning on use (configurable): alerts developers in non-test environments
- Thread-safe: no shared mutable state

```python
# Testing: explicit opt-out, no warning
metrics = NoOpMetrics(warn-on-use=False)

# Production: warning if accidentally used
metrics = NoOpMetrics()  # Emits UserWarning
```

### 4. Log Schema

Structured JSON logs with mandatory fields:

| Field | Required | Example |
|-------|----------|---------|
| `ts` | MUST | `2025-12-26T10:00:00Z` |
| `level` | MUST | `INFO`, `ERROR` |
| `run-id` | MUST | UUID |
| `pipeline` | MUST | `chembl-activity` |
| `stage` | MUST | `extract`, `transform`, `load` |
| `dataset` | SHOULD | `chembl.activity` |
| `record-count` | SHOULD | 1000 |
| `error-type` | On errors | `SCHEMA-VIOLATION` |

## Justification

### 1. Ports Enable Clean Architecture

Application layer must not depend on infrastructure:
- `structlog` is never imported in `application/` or `interfaces/`
- All logging goes through `LoggerPort`
- Verified by architectural test `test-no-structlog-in-application-interfaces`

### 2. NoOp Pattern Simplifies Testing

Tests don't need to mock observability:
- Inject `NoOpLogger`, `NoOpMetrics`, `NoOpTracing`
- Zero overhead in test execution
- No side effects (file writes, network calls)

### 3. Standardized Labels Enable Aggregation

Consistent labeling across all metrics:
- `pipeline`: identifies the data pipeline
- `stage`: extract/transform/load phase
- `run-type`: incremental/backfill/rebuild
- Enables PromQL queries like: `sum(errors-total{pipeline="chembl-activity"}) by (error-code)`

### 4. Runtime Checkable Protocols

All ports use `@runtime-checkable`:
- Enables `isinstance()` checks at runtime
- Validates adapter implementations
- Tested by `tests/architecture/test-port-contracts.py`

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
src/bioetl/domain/ports/
    observability.py        # LoggerPort, MetricsPort, TracingPort, DQMonitorPort
    noop.py                 # NoOpTracing, NoOpMetrics (no I/O, usable by all layers)

src/bioetl/infrastructure/observability/
    logging.py              # StructlogLogger adapter
    unified-logger.py       # UnifiedLogger (Log Schema enforcement)
    logging-config.py       # Centralized structlog configuration
    metrics.py              # Prometheus metric definitions
    prometheus-metrics.py   # PrometheusMetrics adapter
    tracing.py              # OpenTelemetryTracer (real OTel facade adapter)
    noop-logger.py          # NoOpLogger (adapter-level fallback)
    server.py               # Prometheus HTTP server
    anomaly/                # DataQualityMonitor
```

### Dependency Injection

```python
# composition/bootstrap/runtime/observability.py
def bootstrap-metrics-port(settings: Settings) -> MetricsPort:
    if not settings.observability.metrics-enabled:
        return NoOpMetrics(warn-on-use=False)
    return PrometheusMetrics()

def bootstrap-logger-port(
    pipeline: str, run-id: UUID | None = None, log-level: str = "INFO",
) -> LoggerPort:
    return UnifiedLogger(pipeline=pipeline, run-id=run-id or uuid4(), log-level=log-level)

def bootstrap-tracer-port(settings: Settings, service-name: str = "bioetl") -> TracingPort:
    if settings.observability.tracing-enabled:
        return OpenTelemetryTracer(service-name=service-name)
    return NoOpTracing()
```

### Usage in Pipeline

```python
# Application layer uses ports only
class PipelineRunner:
    def --init--(
        self,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort,
    ):
        self.logger = logger
        self.metrics = metrics
        self.tracing = tracing

    async def run-stage(self, stage: str) -> None:
        self.logger.info("stage-started", stage=stage)
        start = time.monotonic()

        # ... processing ...

        duration = time.monotonic() - start
        self.metrics.observe-histogram(
            "pipeline-duration-seconds",
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
- **Type safety**: `@runtime-checkable` validates implementations
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
