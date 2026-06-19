______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-022: NoOp Tracing for Local-Only Deployment

**Date:** 2025-12-30
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

BioETL uses Local-Only Deployment (ADR-010). Distributed tracing (Jaeger, Zipkin,
OpenTelemetry Collector) is relevant for microservice architectures but is redundant
for a local ETL process.

### Current Tracing Needs

| Use Case              | Local Solution                                             |
| --------------------- | ---------------------------------------------------------- |
| Request correlation   | `run_id` in structured logs                                |
| Performance debugging | Prometheus histograms (`pipeline-duration-seconds`)        |
| Error tracking        | Structured error logs with `run_id`, `stage`, `error_type` |
| Batch traceability    | `run_id` + `batch_id` in logs and control-plane artifacts  |

### Distributed Tracing Overhead

Implementing real OpenTelemetry would require:

- Additional dependencies (`opentelemetry-api`, `opentelemetry-sdk`, exporters)
- Running infrastructure (Jaeger/Zipkin/Tempo collector)
- Context propagation between components
- Memory overhead for span buffering

This overhead provides no benefit for single-process local execution.

## Decision

### TracingPort = OpenTelemetry Facade (deliberate choice)

`TracingPort` is intentionally modeled after the **OpenTelemetry Tracing API**.
`get-tracer()` returns an object whose interface mirrors `opentelemetry.trace.Tracer`
(`start-as-current-span`, span context manager, `set-attribute`, `record-exception`).

**Why OTel as the port surface?**

1. **Industry standard** — OTel is the CNCF-graduated vendor-neutral tracing API.
   Adopting its surface avoids inventing a bespoke abstraction.
1. **Zero-cost migration** — switching from `NoOpTracing` to `OpenTelemetryTracer`
   requires only a composition wiring change; application code stays the same.
1. **Ecosystem compatibility** — any OTel-compatible backend (Jaeger, Zipkin, Tempo,
   OTLP Collector) can be plugged in without modifying the port contract.
1. **`Any` return type** — `get-tracer()` returns `Any` to avoid a hard dependency
   on the `opentelemetry` package in the domain layer while preserving the OTel
   calling convention in all implementations.

### Default: NoOpTracing (Null Object Pattern)

Use **Null Object Pattern** (`NoOpTracing`) as the default tracing implementation.
Request correlation is provided via structured logs and control-plane identity
context (`run_id`), not via Prometheus labels.

### Implementation

```python
# Default: NoOpTracing (zero overhead, mirrors OTel API) — lives in src/bioetl/domain/ports/noop/
from bioetl.domain.ports import NoOpTracing
tracing = NoOpTracing()

# Extension point: real OTel adapter (when distributed deployment needed)
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer
tracing = OpenTelemetryTracer(service_name="bioetl")

# Both implementations expose the same OTel calling convention:
otel_tracer = tracing.get_tracer("bioetl.pipeline")
with otel_tracer.start_as_current_span("my-operation", attributes={...}):
    ...  # works identically with NoOp or real OTel
```

### Correlation via run_id (RULES.md §4.5)

Structured logs and control-plane artifacts include `run_id`:

```json
{
  "timestamp": "2025-12-30T10:00:00Z",
  "level": "INFO",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline": "chembl_activity",
  "stage": "transform",
  "record_count": 1000
}
```

This enables:

- Log aggregation: `grep '"run_id"' reports/logs/*.jsonl`
- Control-plane correlation: `run_id` links logs, manifests, ledgers, and HTTP-backed forensic surfaces
- Batch tracing: `run_id` + `batch_id` support granular local debugging without widening Prometheus labels

## Justification

### 1. Zero Overhead

`NoOpTracing` operations are no-ops with negligible CPU/memory cost:

```python
class NoOpTracing:
    def get-tracer(self, name: str) -> NoOpTracer:
        return NoOpTracer()  # Stateless, no allocations per span

    def close(self) -> None:
        return None  # Idempotent
```

### 2. TracingPort Preserved

The port interface remains unchanged, preserving the extension point:

```python
@runtime-checkable
class TracingPort(Protocol):
    def get-tracer(self, name: str) -> Any: ...
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

| File                                             | Purpose                                                         |
| ------------------------------------------------ | --------------------------------------------------------------- |
| `src/bioetl/domain/ports/observability/tracing.py` | TracingPort protocol (OTel facade contract)                   |
| `src/bioetl/domain/ports/noop/_tracing.py`        | NoOpTracing, _NoOpOtelTracer, _NoOpSpan (default)             |
| `src/bioetl/infrastructure/observability/tracing.py` | OpenTelemetryTracer (real OTel adapter) + NoOpTracing import |
| `src/bioetl/composition/bootstrap/runtime/observability.py` | DI wiring (`bootstrap_tracer`)                    |

## Consequences

### Positive

- **(+) Zero overhead**: No memory/CPU cost from span collection
- **(+) No dependencies**: OpenTelemetry packages not required for default usage
- **(+) Simple debugging**: `run_id` in logs and control-plane artifacts is sufficient for local development
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

1. Enable tracing via environment variable:

   ```bash
   export BIOETL_OBSERVABILITY__TRACING_ENABLED=true
   ```

   The bootstrap in `composition/bootstrap/runtime/observability.py` will
   automatically return `OpenTelemetryTracer` instead of `NoOpTracing`.

1. Deploy OpenTelemetry Collector or Jaeger

1. This ADR should be revisited and potentially superseded

## References

- **ADR-010**: Local-Only Deployment Strategy — establishes single-process model
- **ADR-017**: Observability Architecture — defines TracingPort and NoOp pattern
- **ADR-006**: Logger and Metrics Ports — initial observability ports design

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-022-tracing-noop.md`            |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

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
