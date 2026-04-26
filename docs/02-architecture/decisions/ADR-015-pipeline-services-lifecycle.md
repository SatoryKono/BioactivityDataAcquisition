______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-015: Pipeline Services Lifecycle Management

**Date:** 2025-12-24
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

BioETL pipelines use multiple infrastructure components (data sources, storage, locks, checkpoints, metrics, tracing) that require proper initialization and cleanup. Without unified lifecycle management:

1. Resources may leak if exceptions occur during pipeline execution
1. Metrics and traces may not be flushed before process exit
1. Distributed locks may not be released, blocking other workers
1. Each component manages its own lifecycle independently

## Decision

Introduce a centralized lifecycle management pattern through `PipelineServices`:

### 1. Async Context Manager Protocol

`PipelineServices` implements async context manager for unified resource management:

```python
@dataclass(frozen=True)
class PipelineServices:
    data-source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort

    async def --aenter--(self) -> Self:
        """Initialize async resources."""
        await self.data-source.--aenter--()
        return self

    async def --aexit--(self, exc-type, exc-val, exc-tb) -> None:
        """Cleanup all resources."""
        await self.aclose()

    async def aclose(self) -> None:
        """Gracefully close all I/O resources and observability."""
        # Close async I/O services in parallel
        await asyncio.gather(
            self.data-source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return-exceptions=True,
        )
        # Close observability (sync, best-effort)
        self.-close-observability()
```

### 2. Port Lifecycle Contracts

| Port Type      | Lifecycle Method | Sync/Async | Notes                                  |
| -------------- | ---------------- | ---------- | -------------------------------------- |
| DataSourcePort | `aclose()`       | async      | Also supports `--aenter--`/`--aexit--` |
| StoragePort    | `aclose()`       | async      | MUST release Delta table locks         |
| LockPort       | `aclose()`       | async      | MUST release held locks                |
| CheckpointPort | `aclose()`       | async      | MUST flush pending writes              |
| QuarantinePort | `aclose()`       | async      | MUST flush buffer                      |
| MetricsPort    | `close()`        | sync       | Flush pending metrics                  |
| TracingPort    | `close()`        | sync       | Flush pending spans                    |
| LoggerPort     | -                | -          | No lifecycle (managed externally)      |

### 3. Graceful Shutdown Integration

When SIGTERM/SIGINT is received (see ADR-008):

1. `PipelineRunner` catches signal
1. Stops extracting new records
1. Waits for current batch to complete
1. Calls `services.aclose()` to cleanup all resources
1. Exits with code 0

### 4. Error Handling During Cleanup

Cleanup errors are logged but don't prevent other resources from being cleaned:

```python
results = await asyncio.gather(..., return-exceptions=True)
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
    ASYNC-IO-PORTS = [
        "DataSourcePort", "StoragePort", "LockPort",
        "CheckpointPort", "QuarantinePort"
    ]

    @pytest.mark.parametrize("port-name", ASYNC-IO-PORTS)
    def test-async-ports-have-aclose-method(self, port-name):
        """All async I/O ports MUST have aclose() method."""
        port-class = getattr(ports, port-name)
        assert hasattr(port-class, "aclose")

class TestObservabilityPortLifecycle:
    OBSERVABILITY-PORTS = ["MetricsPort", "TracingPort"]

    @pytest.mark.parametrize("port-name", OBSERVABILITY-PORTS)
    def test-observability-ports-have-close-method(self, port-name):
        """Observability ports MUST have close() method."""
        port-class = getattr(ports, port-name)
        assert hasattr(port-class, "close")
```

## References

- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — services assembled in composition
- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports — defines observability ports
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy — shutdown coordination
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup — async cleanup methods
- [ADR-020](ADR-020-basepipeline-decomposition.md): BasePipeline Decomposition — PipelineServices design
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates — uses PipelineServices lifecycle

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                 |
| ------------ | -------------------------------------------------------------------------- | ------ | ---------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-015-pipeline-services-lifecycle.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                               |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                         |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`     |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                             |

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
