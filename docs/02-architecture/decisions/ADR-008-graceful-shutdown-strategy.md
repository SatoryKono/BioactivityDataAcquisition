______________________________________________________________________

Version: 1.0.0
Status: Superseded (signal handlers removed; shutdown handled in canonical CLI domain command modules and application/core/lifecycle/shutdown.py)
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-008: Graceful Shutdown Strategy

**Date:** 2025-12-22
**Status:** Superseded (signal handlers removed; shutdown handled in canonical CLI domain command modules and application/core/lifecycle/shutdown.py)
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team

> **Superseded:** Signal handlers удалены 2025-12-31.
> Graceful shutdown обрабатывается в canonical CLI domain command modules
> (`interfaces/cli/commands/domains/run/command.py`,
> `interfaces/cli/commands/domains/run_all/command.py`,
> `interfaces/cli/commands/domains/composite/command.py`)
> и `application/core/lifecycle/shutdown.py`.
> orchestration/ модуль пуст.

## Context

ETL pipelines process large datasets in batches, maintaining state via checkpoints and holding runtime locks. An abrupt shutdown (kill -9, OOM, etc.) can leave the system in an inconsistent state: orphaned locks, missing checkpoints, partially written batches. A coordinated shutdown mechanism was needed to ensure data integrity.

> **Update 2025-12-31:** Signal handlers in `interfaces/orchestration/signals.py` were removed. Shutdown is now handled at CLI level via `KeyboardInterrupt` in the retained public command modules `interfaces/cli/commands/run.py`, `run_all.py`, and `run_composite.py`, with helper logic split under `interfaces/cli/commands/domains/*`. See `application/core/lifecycle/shutdown.py` for `ShutdownSignal`. The architecture diagram and implementation details below reflect the original design; the interfaces-layer signal handler box is no longer present.

## Decision

We have implemented a **two-layer shutdown coordination system**:

1. **`ShutdownSignal`** (`application/core/lifecycle/shutdown.py`): Application-level signal object shared across components
1. **OS Signal Handlers** (`interfaces/orchestration/signals.py`): Translate SIGTERM/SIGINT to ShutdownSignal (removed 2025-12-31; see update note above)

Key characteristics:

- Idempotent shutdown requests
- Async-friendly with `asyncio.Event`
- Propagates to all pipeline components via dependency injection
- Components check signal before and after critical operations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     OS / Orchestrator                        │
│                      (SIGTERM, SIGINT)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Signal Handlers (interfaces layer)              │
│         setup-shutdown-handlers(shutdown-signal)             │
└─────────────────────────┬───────────────────────────────────┘
                          │ shutdown-signal.request()
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               ShutdownSignal (application layer)             │
│                    asyncio.Event based                       │
└───────────┬─────────────┬─────────────┬─────────────────────┘
            │             │             │
            ▼             ▼             ▼
       ┌─────────┐  ┌──────────┐  ┌──────────────┐
       │Executor │  │Checkpoint│  │ Lock Manager │
       │         │  │ Manager  │  │              │
       └─────────┘  └──────────┘  └──────────────┘
```

## Justification

### 1. Separation of Concerns

| Layer          | Responsibility                          |
| -------------- | --------------------------------------- |
| interfaces     | Captures OS signals, framework events   |
| application    | Coordinates shutdown via shared signal  |
| infrastructure | Releases resources (locks, connections) |

This follows the hexagonal architecture: interfaces translate external events, application orchestrates, infrastructure cleans up.

### 2. Checkpoint-First Shutdown

On shutdown signal:

1. Current batch completes (no mid-batch abort)
1. Checkpoint is saved with last processed watermark
1. Lock heartbeat stops
1. Lock is released
1. Connections are closed

This ensures resumability—next run can continue from saved checkpoint.

### 3. Lock Safety Invariant

**Critical rule**: If lock is lost during shutdown, the pipeline MUST NOT write any data.

```python
# In executor
if shutdown-signal.is-requested:
    await checkpoint-manager.save()
    return  # Exit before next write

# Lock loss also triggers shutdown
if not await lock.is-held():
    shutdown-signal.request()
```

This prevents split-brain scenarios where multiple workers might write conflicting data.

### 4. Idempotent Shutdown

Multiple shutdown requests (e.g., SIGTERM followed by SIGINT) are handled gracefully:

```python
def request(self) -> None:
    if not self.-requested:  # Only act once
        self.-requested = True
        self.-event.set()
```

## Implementation Details

### ShutdownSignal

```python
@dataclass
class ShutdownSignal:
    -requested: bool = field(default=False, init=False)
    -event: asyncio.Event = field(default-factory=asyncio.Event, init=False)

    @property
    def is-requested(self) -> bool:
        return self.-requested

    def request(self) -> None:
        if not self.-requested:
            self.-requested = True
            self.-event.set()

    async def wait(self) -> None:
        await self.-event.wait()
```

### Signal Handler Setup

```python
def setup-shutdown-handlers(shutdown-signal: ShutdownSignal) -> None:
    def signal-handler(signum: int, -: Any) -> None:
        logger.warning(f"Received {signal.strsignal(signum)}, initiating shutdown")
        shutdown-signal.request()

    signal.signal(signal.SIGTERM, signal-handler)
    signal.signal(signal.SIGINT, signal-handler)
```

### Integration Points

```python
# Executor checks before each batch
async def execute(self, watermark, limit):
    for batch in self.fetch-batches():
        if self.shutdown-signal.is-requested:
            await self.save-checkpoint()
            break
        await self.process-batch(batch)

# Runner passes signal to all components
runner = PipelineRunner(shutdown-signal=shutdown-signal, executor=executor, ...)
```

## Alternatives Considered

### 1. asyncio.CancelledError Propagation

Rejected because:

- Cancellation is abrupt, doesn't allow checkpoint saving
- Hard to distinguish between timeout and shutdown
- Less control over cleanup order

### 2. Context Manager / RAII Pattern

Rejected because:

- Doesn't work well with async generators
- Cleanup order is implicit (reverse of acquisition)
- Less visibility into shutdown state

### 3. Global Singleton Signal

Rejected because:

- Violates dependency injection principle
- Hard to test (global state)
- Doesn't work for multiple concurrent pipelines

## Consequences

### Positive

- Clean shutdown with checkpoint preservation
- Resumable pipelines after interruption
- Lock safety guaranteed
- Works with Kubernetes graceful termination
- Testable via signal injection

### Negative

- **Main thread requirement**: Signal handlers can only be set in main thread. Mitigated by try/except in setup.
- **Blocking operations**: Long-running sync operations can delay shutdown. Mitigated by using async throughout.

> **Note (ADR-010):** BioETL uses Local-Only deployment. The Kubernetes section below is retained for historical reference but is not applicable to the current architecture.

## Kubernetes Integration

```yaml
spec:
  terminationGracePeriodSeconds: 300  # 5 minutes for checkpoint
  containers:
  - name: bioetl
    lifecycle:
      preStop:
        exec:
          command: ["sleep", "5"]  # Allow signal propagation
```

The 5-minute grace period allows:

1. Current batch to complete (~30s max)
1. Checkpoint to be saved (~10s)
1. Lock release and cleanup (~5s)
1. Buffer for slow operations

## References

- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking (MemoryLock) — lock safety (Updated: 2025-12-23)
- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation — failure handling coordination (Updated: 2025-12-22)
- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — MemoryLock shutdown behavior (Updated: 2025-12-23)
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — aclose() during shutdown (Updated: 2025-12-24)
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — shutdown on critical errors (Updated: 2025-12-26)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                                                                                                                    |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-008-graceful-shutdown-strategy.md`                                                                                                     |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Superseded (signal handlers removed; shutdown handled in canonical CLI domain command modules and application/core/lifecycle/shutdown.py)` |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                                                                                                                            |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`                                                                                                        |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                                                                                                                |

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
