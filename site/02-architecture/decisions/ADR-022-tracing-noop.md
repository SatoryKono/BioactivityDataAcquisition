# ADR-022: NoOp Tracing for Local-Only Deployment

**Status:** Accepted
**Date:** 2025-12-30
**Decision makers:** @BioETL-Team
**Extends:** ADR-010 (Local-Only Deployment), ADR-017 (Observability Architecture)

## Context

BioETL uses Local-Only Deployment (ADR-010). Distributed tracing (Jaeger, Zipkin,
OpenTelemetry Collector) is relevant for microservice architectures but is redundant
for a local ETL process.

### Current Tracing Needs

| Use Case | Local Solution |
|----------|---------------|
| Request correlation | `run_id` in structured logs |
| Performance debugging | Prometheus histograms (`pipeline_duration_seconds`) |
| Error tracking | Structured error logs with `run_id`, `stage`, `error_type` |
| Batch traceability | `run_id` + `batch_id` in logs and metrics |

### Distributed Tracing Overhead

Implementing real OpenTelemetry would require:
- Additional dependencies (`opentelemetry-api`, `opentelemetry-sdk`, exporters)
- Running infrastructure (Jaeger/Zipkin/Tempo collector)
- Context propagation between components
- Memory overhead for span buffering

This overhead provides no benefit for single-process local execution.

## The Decision

Use **Null Object Pattern** (`NoOpTracing`) as the default tracing implementation.
Request correlation is provided via `run_id` in structured logs.

### Implementation

```python
# Default: NoOpTracing (zero overhead)
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
tracing = NoOpTracing()

# Extension point: OpenTelemetryTracer (when distributed deployment needed)
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer
tracing = OpenTelemetryTracer(service_name="bioetl")
```

### Correlation via run_id (RULES.md §4.5)

All structured logs include `run_id`:

```json
{
  "ts": "2025-12-30T10:00:00Z",
  "level": "INFO",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline": "chembl_activity",
  "stage": "transform",
  "record_count": 1000
}
```

This enables:
- Log aggregation: `grep run_id=<uuid> logs/*.jsonl`
- Metrics correlation: labels include `run_id` where appropriate
- Batch tracing: `run_id` + `batch_id` for granular tracking

## Justification

### 1. Zero Overhead

`NoOpTracing` operations are no-ops with negligible CPU/memory cost:

```python
class NoOpTracing:
    def get_tracer(self, name: str) -> NoOpTracer:
        return NoOpTracer()  # Stateless, no allocations per span

    def close(self) -> None:
        self._closed = True  # Idempotent
```

### 2. TracingPort Preserved

The port interface remains unchanged, preserving the extension point:

```python
@runtime_checkable
class TracingPort(Protocol):
    def get_tracer(self, name: str) -> Any: ...
    def close(self) -> None: ...
```

### 3. OpenTelemetry Ready

`OpenTelemetryTracer` class exists in `tracing.py` for future use:
- Supports OTLP export (production) and Console export (debug)
- Graceful shutdown with span flushing
- Compatible with TracingPort interface

### 4. Consistency with ADR-010

Local-Only Deployment principle:
- No external infrastructure dependencies
- Single-process execution model
- File-based storage (Bronze/Silver/Gold)

## Implementation Files

| File | Purpose |
|------|---------|
| `infrastructure/observability/noop_tracing.py` | NoOpTracing, NoOpTracer (default) |
| `infrastructure/observability/tracing.py` | OpenTelemetryTracer (extension point) |
| `domain/ports/observability.py` | TracingPort protocol |
| `composition/factories/observability.py` | DI wiring (returns NoOpTracing) |

## Consequences

### Positive

- **(+) Zero overhead**: No memory/CPU cost from span collection
- **(+) No dependencies**: OpenTelemetry packages not required for default usage
- **(+) Simple debugging**: `run_id` in logs sufficient for local development
- **(+) Extension point preserved**: TracingPort + OpenTelemetryTracer ready for future
- **(+) Consistent with ADR-010**: No external infrastructure needed

### Negative

- **(-) No distributed tracing**: Cannot trace requests across services (not needed for local ETL)
- **(-) No visual timeline**: No Jaeger/Zipkin UI for span visualization

### Migration Path (Future)

If distributed deployment becomes necessary:

1. Install OpenTelemetry dependencies:
   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
   ```

2. Update factory in `composition/factories/observability.py`:
   ```python
   def create_tracing(config: Config) -> TracingPort:
       if config.tracing_enabled:
           return OpenTelemetryTracer(service_name="bioetl")
       return NoOpTracing()
   ```

3. Deploy OpenTelemetry Collector or Jaeger

4. This ADR should be revisited and potentially superseded

## Related ADRs

- **ADR-010**: Local-Only Deployment Strategy — establishes single-process model
- **ADR-017**: Observability Architecture — defines TracingPort and NoOp pattern
- **ADR-006**: Logger and Metrics Ports — initial observability ports design
