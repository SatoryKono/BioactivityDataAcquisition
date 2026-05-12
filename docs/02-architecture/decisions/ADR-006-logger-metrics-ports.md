______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-006: Ports for Logger and Metrics

**Date:** 2025-12-18
**Status:** Accepted
**Last updated:** 2025-12-25
**Decision makers:** @BioETL-Team

## Context

Logger and metrics dependencies were not consistently formalized as ports. The logger was typed as a concrete `structlog.BoundLogger` in `PipelineServices`, while metrics already had a proper `MetricsPort`. This inconsistency violated the Ports & Adapters architecture principle.

Note: `domain/ports.py` was reorganized into a package `domain/ports/` with a facade. Import: `from bioetl.domain.ports import LoggerPort`.

## Decision

We have chosen to:

1. **Create `LoggerPort`** in `domain/ports/` package as a formal Protocol for logging
1. **Keep `MetricsPort`** as-is (already properly defined)
1. **Use ports consistently** in `PipelineServices` for both logger and metrics
1. **Maintain backward compatibility** via `BoundLogger` alias in `domain/context.py`

## Justification

### 1. Architectural Consistency

All external dependencies should be abstracted through ports:

| Dependency  | Port             | Location        |
| ----------- | ---------------- | --------------- |
| Data Source | `DataSourcePort` | `domain/ports/` |
| Storage     | `BronzeStoragePort` / `SilverStoragePort` / `GoldStoragePort` / `MergedStoragePort` | `domain/ports/storage/` |
| Lock        | `LockPort`       | `domain/ports/` |
| Checkpoint  | `CheckpointPort` | `domain/ports/` |
| Quarantine  | `QuarantinePort` | `domain/ports/` |
| Metrics     | `MetricsPort`    | `domain/ports/` |
| **Logger**  | **`LoggerPort`** | `domain/ports/` |

### 2. Testability

Using a port allows easy mocking in tests:

```python
# Before: tight coupling to structlog
logger: "structlog.BoundLogger"

# After: protocol-based abstraction
logger: LoggerPort

# Tests can use any implementation
mock - logger = MagicMock(spec=LoggerPort)
```

### 3. Future Flexibility

The abstraction allows switching logging implementations without changing application code:

- structlog (current)
- loguru
- Standard library logging
- Custom implementations

### 4. Domain Layer Purity

The domain layer should not depend on infrastructure details. By defining `LoggerPort` in `domain/ports/`, we ensure the domain only depends on an abstract contract, not on `structlog`.

## Implementation Details

### LoggerPort Definition

```python
@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging."""

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Return a new logger with additional bound context."""
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
        """Emit an error log event with exception information."""
        ...
```

**Note:** The first parameter `_event` (with underscore prefix) follows structlog convention to indicate it's a positional marker. Return type is `Any` because structlog returns implementation-defined values per the API contract.

### Backward Compatibility

The `BoundLogger` alias (previously in `domain/context.py`) has been fully removed.
All code now uses `LoggerPort` directly from `bioetl.domain.ports`.

### PipelineServices Update

```python
@dataclass(frozen=True)
class PipelineServices:
    data - source: DataSourcePort
    storage: BronzeStoragePort | SilverStoragePort | GoldStoragePort | MergedStoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort  # Already a port
    logger: LoggerPort  # Now also a port (was structlog.BoundLogger)
```

## Alternatives Considered

### 1. Keep structlog typing

Rejected because:

- Violates Ports & Adapters architecture
- Creates tight coupling to infrastructure
- Makes testing harder
- Inconsistent with other dependencies

### 2. Create separate LoggingPort with different interface

Rejected because:

- The structlog interface (`bind`, `info`, `error`, etc.) is already a good abstraction
- No benefit in creating a different interface
- Would require adapters for existing code

### 3. Move LoggerPort to a separate file

Rejected because:

- All other ports are in `domain/ports/` package
- Keeping them together improves discoverability
- No circular dependency issues

## Consequences

### Positive

- Consistent architecture across all dependencies
- Improved testability
- Future flexibility for logging implementations
- Clean domain layer without infrastructure dependencies

### Negative

- Minor: Existing code using `BoundLogger` still works but should migrate to `LoggerPort`

## Rollout

1. New code should use `LoggerPort` directly
1. Existing code using `BoundLogger` continues to work
1. Gradual migration as files are modified

## References

- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes — logging constraints for reproducibility
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — MetricsPort lifecycle management
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture — extends this with TracingPort and full observability stack
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement — enforces LoggerPort usage in all layers
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — applies NoOp pattern established here to tracing

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-006-logger-metrics-ports.md`    |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

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
