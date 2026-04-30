______________________________________________________________________

Version: 1.1.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-12'

______________________________________________________________________

# ADR-017: Observability Architecture

**Date:** 2025-12-26
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

BioETL pipelines require comprehensive observability for debugging, performance monitoring, and operational alerting. The observability stack must follow the Ports & Adapters architecture to maintain testability and avoid infrastructure dependencies in domain/application layers.

## Decision

BioETL uses a **port-based observability architecture** with domain-owned
contracts, application-owned emission semantics, infrastructure-owned adapters,
and composition-owned runtime wiring.

The canonical runtime contract is:

- observability dependencies enter ordinary runs only through injected ports
- metric names are `bioetl_*` and `snake_case`
- structured logs use `timestamp`, `run_id`, `pipeline`, and `stage`
- `PipelineObserver` is the sanctioned lifecycle emitter for ordinary pipeline
  runs
- composition owns the supported bootstrap and diagnostics assembly seams
- compatibility layers may exist, but they must delegate back to canonical
  runtime seams and be documented explicitly

### 1. Observability Ports as Formal Protocols

All observability concerns are abstracted through ports in `domain/ports/observability/`:

**LoggerPort** (`domain/ports/observability/logging.py`):

```python
@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging."""

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Return a new logger with additional bound context key-value pairs."""
        ...

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit an informational log event."""
        ...

    def warning(
        self, _event: str, **kwargs: Any
    ) -> Any:  # Any: structlog-compatible API
        """Emit a warning log event."""
        ...

    def error(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit an error log event."""
        ...

    def debug(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit a debug log event."""
        ...

    def exception(
        self, _event: str, **kwargs: Any
    ) -> Any:  # Any: structlog-compatible API
        """Emit an error log event with current exception information attached."""
        ...
```

**MetricsPort** (`domain/ports/observability/metrics.py`):

```python
@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """Record a histogram observation."""
        ...

    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        """Increment a counter metric."""
        ...

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Set a gauge metric value."""
        ...

    def close(self) -> None:
        """Close and cleanup metrics resources."""
        ...
```

**TracingPort** (`domain/ports/observability/tracing.py`):

```python
@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing — an OpenTelemetry Tracing API facade.

    Deliberately modeled after the OTel API: get_tracer() returns an
    OTel-compatible Tracer (start_as_current_span, Span context manager).
    This is an intentional design choice — see ADR-022 for the rationale.
    """

    def get_tracer(self, name: str) -> Any:
        """Get or create a tracer instance."""
        ...

    def close(self) -> None:
        """Close and cleanup tracing resources."""
        ...
```

### 2. Prometheus Metrics with Standardized Labels

Metrics are exposed at
`http://localhost:${BIOETL_METRICS_PORT:-8000}/metrics` when the metrics server
is enabled.

Canonical naming rules:

- prefix: `bioetl_`
- case: `snake_case`
- counters use suffix `_total`
- duration families use `_seconds` or `_ms`
- labels remain bounded and MUST NOT include `run_id`, filesystem paths,
  manifest identifiers, or other high-cardinality runtime anchors
- adapter `endpoint` labels MUST be normalized to bounded route templates
- filter `source_kind` labels MUST use a bounded source vocabulary; raw file/path
  identity MUST NOT be published as Prometheus labels
- adapter `operation` labels MUST use reviewed bounded vocabularies; unknown
  values collapse to `other`
- runtime `stage` and lifecycle/composite `phase` labels MUST use canonical
  bounded vocabularies rather than ad hoc free-text values

Representative runtime families:

| Metric                                  | Type      | Labels                            | Description                        |
| --------------------------------------- | --------- | --------------------------------- | ---------------------------------- |
| `bioetl_pipeline_duration_seconds`      | Histogram | pipeline, stage, status, run_type | Pipeline/stage duration            |
| `bioetl_records_processed_total`        | Counter   | pipeline, stage, run_type         | Processed record count             |
| `bioetl_errors_total`                   | Counter   | pipeline, stage, error_code       | Error taxonomy counts              |
| `bioetl_circuit_breaker_state`          | Gauge     | adapter                           | 0=Closed, 1=Half-Open, 2=Open      |
| `bioetl_dq_validation_score`            | Gauge     | pipeline, entity                  | DQ score in `[0,1]`                |
| `bioetl_data_freshness_seconds`         | Gauge     | pipeline, entity                  | Application-owned ingestion anchor |
| `bioetl_postrun_phase_events_total`     | Counter   | pipeline, phase, status           | Bounded postrun subphase outcomes  |
| `bioetl_postrun_phase_duration_seconds` | Histogram | pipeline, phase, status           | Bounded postrun subphase durations |

Legacy `kebab-case` names such as `pipeline-duration-seconds` are not part of
the current runtime contract.

### 3. NoOp Implementations for Testing and Graceful Degradation

`NoOpMetrics` and `NoOpTracing` live in `domain/ports/noop/` so they can be
used without infrastructure dependencies. `NoOpLogger` remains an
adapter-level fallback in infrastructure.

| Port          | NoOp Implementation | Location                                      |
| ------------- | ------------------- | --------------------------------------------- |
| `LoggerPort`  | `NoOpLogger`        | `infrastructure/observability/noop_logger.py` |
| `MetricsPort` | `NoOpMetrics`       | `domain/ports/noop/_metrics.py`               |
| `TracingPort` | `NoOpTracing`       | `domain/ports/noop/_tracing.py`               |

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

| Field          | Required  | Example                        |
| -------------- | --------- | ------------------------------ |
| `timestamp`    | MUST      | `2026-04-12T13:02:47Z`         |
| `level`        | MUST      | `info`, `warning`, `error`     |
| `run_id`       | MUST      | UUID                           |
| `pipeline`     | MUST      | `chembl_activity`              |
| `stage`        | MUST      | `extract`, `transform`, `load` |
| `dataset`      | SHOULD    | `chembl.activity`              |
| `record_count` | SHOULD    | 1000                           |
| `error_type`   | On errors | `SCHEMA_VIOLATION`             |

Compatibility notes:

- `timestamp` is the canonical runtime field name
- downstream normalization may still accept `ts` as an alias, but `ts` is not
  the canonical emitted field name
- `extra={...}` is accepted as compatibility input by `UnifiedLogger`, then
  flattened into top-level structured fields with explicit kwargs taking
  precedence

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
- `stage`: bounded runtime stage label
- `run-type`: incremental/backfill/rebuild
- Enables PromQL queries like:
  `sum(bioetl_errors_total{pipeline="chembl_activity"}) by (error_code)`

### 4. Runtime Checkable Protocols

All ports use `@runtime-checkable`:

- Enables `isinstance()` checks at runtime
- Validates adapter implementations
- Tested by `tests/architecture/test_port_contracts.py`

## Implementation Details

### Port Location

```
src/bioetl/domain/ports/observability/
    logging.py
    metrics.py
    tracing.py
    dq_monitor.py
src/bioetl/domain/ports/audit.py
```

### Adapter Location

```
src/bioetl/domain/ports/observability/
    logging.py
    metrics.py
    tracing.py
    dq_monitor.py
src/bioetl/domain/ports/noop/
    _metrics.py
    _tracing.py
src/bioetl/domain/ports/audit.py

src/bioetl/infrastructure/observability/
    unified_logger.py
    logging_config.py
    prometheus_metrics.py
    prometheus_metric_registries.py
    tracing.py
    noop_logger.py
    server.py
    anomaly/monitor.py

src/bioetl/composition/bootstrap/runtime/
    logger_bootstrap.py
    metrics_bootstrap.py
    tracing_bootstrap.py
    observability_bundle.py
src/bioetl/composition/observability_api.py
```

### Dependency Injection

```python
# composition/bootstrap/runtime/logger_bootstrap.py
logger = bootstrap_logger_port(pipeline, run_id, log_level)

# composition/bootstrap/runtime/metrics_bootstrap.py
metrics = bootstrap_metrics_port(settings)

# composition/bootstrap/runtime/tracing_bootstrap.py
tracer = bootstrap_tracer_port(settings, service_name="bioetl")

# composition/bootstrap/runtime/observability_bundle.py
bundle = bootstrap_observability_bundle_impl(
    pipeline=pipeline,
    run_id=run_id,
    settings=settings,
    log_level=log_level,
    logger_bootstrapper=bootstrap_logger_port,
    tracer_bootstrapper=bootstrap_tracer_port,
    metrics_bootstrapper=bootstrap_metrics_port,
    dq_monitor_bootstrapper=bootstrap_dq_monitor,
    preflight_validator=validate_observability_preflight_impl,
)
```

`bootstrap_*_port` names in this layer are sanctioned composition bootstrap
factory functions, not domain `*Port` contract definitions. The reviewed
allowlist is governed by `configs/quality/layered_suffix_policy.yaml` and must
not expand without explicit naming-policy review.

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

    async def run-stage(self, stage: str) -> None:
        self.logger.info("stage_started", stage=stage)
        start = time.monotonic()

        # ... processing ...

        duration = time.monotonic() - start
        self.metrics.observe_histogram(
            "bioetl_pipeline_duration_seconds",
            duration,
            {"pipeline": self.name, "stage": stage, "status": "success"},
        )
```

### 5. Runtime Publication Boundaries

- `PipelineObserver` is the canonical lifecycle emitter for ordinary runs
- `PreflightService` and `HealthAggregator` may build typed reports, but
  runner-owned observer emission is the sanctioned runtime publication path for
  preflight lifecycle signals
- `DataQualityService` derives a canonical DQ timestamp from the same
  application-owned freshness anchor published via
  `bioetl_data_freshness_seconds`, and passes that timestamp into
  `DQMonitorPort.check_quality(...)` and
  `DQMonitorPort.update_baseline_from_metrics(...)`
- `PostrunService` publishes nested spans plus bounded low-cardinality metrics
  and logs for `dq_evaluation`, `dq_reports`, `compaction`, `vacuum`, and
  `final_metadata`

### 6. Public Seams and Compatibility Layers

The canonical public seam for observability-related diagnostics and composition
assembly is `bioetl.composition.observability_api`.

Remaining compatibility layers are explicit:

- `bioetl.interfaces.observability` remains a compatibility facade for
  interface-layer consumers and delegates back to the composition API
- `UnifiedLogger` accepts `extra={...}` compatibility input but emits flat
  top-level structured fields
- downstream log normalization may still accept `ts`, but runtime emission uses
  `timestamp`

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
- **Consistent labels**: Standard aggregation patterns in dashboards and alerts

### Negative

- **Boilerplate**: Port + Adapter + NoOp for each concern
- **Indirection**: One level of abstraction vs direct calls
- **Learning curve**: Developers must use ports, not direct imports

## References

- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports — initial decision for LoggerPort/MetricsPort
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes — logging constraints for reproducibility
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — metric integration
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — logging integration
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement — enforces this architecture
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — NoOp pattern for tracing defined here
- [Observability Layers](../observability-layers.md): current layer responsibilities
- [Observability Specification](../../04-reference/contracts/observability.md): current runtime contract and metric catalog
- [Observability Checklist](../../05-operations/runbooks/observability-checklist.md): operator validation and diagnostics path

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                |
| ------------ | -------------------------------------------------------------------------- | ------ | --------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-017-observability-architecture.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                              |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                        |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`    |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                            |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
