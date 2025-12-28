# ADR-015: Pipeline Services Lifecycle Management

**Status:** Accepted
**Date:** 2025-12-24
**Deciders:** BioETL Team

## Context

BioETL pipelines use multiple infrastructure components (data sources, storage, locks, checkpoints, metrics, tracing) that require proper initialization and cleanup. Without unified lifecycle management:

1. Resources may leak if exceptions occur during pipeline execution
2. Metrics and traces may not be flushed before process exit
3. Distributed locks may not be released, blocking other workers
4. Each component manages its own lifecycle independently

## Decision

Introduce a centralized lifecycle management pattern through `PipelineServices`:

### 1. Async Context Manager Protocol

`PipelineServices` implements async context manager for unified resource management:

```python
@dataclass(frozen=True)
class PipelineServices:
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort

    async def __aenter__(self) -> Self:
        """Initialize async resources."""
        await self.data_source.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cleanup all resources."""
        await self.aclose()

    async def aclose(self) -> None:
        """Gracefully close all I/O resources and observability."""
        # Close async I/O services in parallel
        await asyncio.gather(
            self.data_source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return_exceptions=True,
        )
        # Close observability (sync, best-effort)
        self._close_observability()
```

### 2. Port Lifecycle Contracts

| Port Type | Lifecycle Method | Sync/Async | Notes |
|-----------|------------------|------------|-------|
| DataSourcePort | `aclose()` | async | Also supports `__aenter__`/`__aexit__` |
| StoragePort | `aclose()` | async | MUST release Delta table locks |
| LockPort | `aclose()` | async | MUST release held locks |
| CheckpointPort | `aclose()` | async | MUST flush pending writes |
| QuarantinePort | `aclose()` | async | MUST flush buffer |
| MetricsPort | `close()` | sync | Flush pending metrics |
| TracingPort | `close()` | sync | Flush pending spans |
| LoggerPort | - | - | No lifecycle (managed externally) |

### 3. Graceful Shutdown Integration

When SIGTERM/SIGINT is received (see ADR-008):

1. `PipelineRunner` catches signal
2. Stops extracting new records
3. Waits for current batch to complete
4. Calls `services.aclose()` to cleanup all resources
5. Exits with code 0

### 4. Error Handling During Cleanup

Cleanup errors are logged but don't prevent other resources from being cleaned:

```python
results = await asyncio.gather(..., return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        self.logger.error("Error during service shutdown", error=result)
```

## Consequences

### Positive

- **Unified cleanup:** All resources cleaned through single `aclose()` call
- **Parallel cleanup:** Async I/O resources closed concurrently for speed
- **Graceful degradation:** One failing cleanup doesn't block others
- **Testability:** Easy to verify all ports have lifecycle methods
- **Idempotent:** Safe to call `close()`/`aclose()` multiple times

### Negative

- **Frozen dataclass:** Cannot modify services after creation
- **All-or-nothing:** Must provide all services at construction time

## Architecture Tests

Lifecycle contracts are enforced by architecture tests:

```python
# tests/architecture/test_port_contracts.py

class TestAsyncPortLifecycle:
    ASYNC_IO_PORTS = [
        "DataSourcePort", "StoragePort", "LockPort",
        "CheckpointPort", "QuarantinePort"
    ]

    @pytest.mark.parametrize("port_name", ASYNC_IO_PORTS)
    def test_async_ports_have_aclose_method(self, port_name):
        """All async I/O ports MUST have aclose() method."""
        port_class = getattr(ports, port_name)
        assert hasattr(port_class, "aclose")

class TestObservabilityPortLifecycle:
    OBSERVABILITY_PORTS = ["MetricsPort", "TracingPort"]

    @pytest.mark.parametrize("port_name", OBSERVABILITY_PORTS)
    def test_observability_ports_have_close_method(self, port_name):
        """Observability ports MUST have close() method."""
        port_class = getattr(ports, port_name)
        assert hasattr(port_class, "close")
```

## Related ADRs

- [ADR-006: Logger and Metrics as Ports](ADR-006-logger-metrics-ports.md)
- [ADR-008: Graceful Shutdown Strategy](ADR-008-graceful-shutdown-strategy.md)
- [ADR-020: BasePipeline Decomposition](ADR-020-basepipeline-decomposition.md)
