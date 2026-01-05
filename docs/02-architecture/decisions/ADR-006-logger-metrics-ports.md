# ADR-006: Ports for Logger and Metrics

**Status:** Accepted
**Date:** 2025-12-18
**Last Updated:** 2025-12-25
**Decision makers:** @BioETL-Team

## Context

Logger and metrics dependencies were not consistently formalized as ports. The logger was typed as a concrete `structlog.BoundLogger` in `PipelineServices`, while metrics already had a proper `MetricsPort`. This inconsistency violated the Ports & Adapters architecture principle.

Note: `domain/ports.py` was reorganized into a package `domain/ports/` with a facade. Import: `from bioetl.domain.ports import LoggerPort`.

## The Decision

We have chosen to:

1. **Create `LoggerPort`** in `domain/ports.py` as a formal Protocol for logging
2. **Keep `MetricsPort`** as-is (already properly defined)
3. **Use ports consistently** in `PipelineServices` for both logger and metrics
4. **Maintain backward compatibility** via `BoundLogger` alias in `domain/context.py`

## Justification

### 1. Architectural Consistency

All external dependencies should be abstracted through ports:

| Dependency | Port | Location |
|------------|------|----------|
| Data Source | `DataSourcePort` | `domain/ports.py` |
| Storage | `StoragePort` | `domain/ports.py` |
| Lock | `LockPort` | `domain/ports.py` |
| Checkpoint | `CheckpointPort` | `domain/ports.py` |
| Quarantine | `QuarantinePort` | `domain/ports.py` |
| Metrics | `MetricsPort` | `domain/ports.py` |
| **Logger** | **`LoggerPort`** | `domain/ports.py` |

### 2. Testability

Using a port allows easy mocking in tests:

```python
# Before: tight coupling to structlog
logger: "structlog.BoundLogger"

# After: protocol-based abstraction
logger: LoggerPort

# Tests can use any implementation
mock_logger = MagicMock(spec=LoggerPort)
```

### 3. Future Flexibility

The abstraction allows switching logging implementations without changing application code:
- structlog (current)
- loguru
- Standard library logging
- Custom implementations

### 4. Domain Layer Purity

The domain layer should not depend on infrastructure details. By defining `LoggerPort` in `domain/ports.py`, we ensure the domain only depends on an abstract contract, not on `structlog`.

## Implementation Details

### LoggerPort Definition

```python
class LoggerPort(Protocol):
    """Port for structured logging."""

    def bind(self, **kwargs: Any) -> "LoggerPort": ...
    def info(self, msg: str, **kwargs: Any) -> None: ...
    def warning(self, msg: str, **kwargs: Any) -> None: ...
    def error(self, msg: str, **kwargs: Any) -> None: ...
    def debug(self, msg: str, **kwargs: Any) -> None: ...
    def exception(self, msg: str, **kwargs: Any) -> None: ...
```

### Backward Compatibility

To avoid breaking existing code, `BoundLogger` is preserved as an alias:

```python
# domain/context.py
from bioetl.domain.ports import LoggerPort

# Backward compatibility alias
BoundLogger = LoggerPort
```

### PipelineServices Update

```python
@dataclass(frozen=True)
class PipelineServices:
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort    # Already a port
    logger: LoggerPort      # Now also a port (was structlog.BoundLogger)
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
- All other ports are in `domain/ports.py`
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

## Migration Path

1. New code should use `LoggerPort` directly
2. Existing code using `BoundLogger` continues to work
3. Gradual migration as files are modified

## Related ADRs

- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes — logging constraints for reproducibility
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — MetricsPort lifecycle management
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture — extends this with TracingPort and full observability stack
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement — enforces LoggerPort usage in all layers
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing — applies NoOp pattern established here to tracing
