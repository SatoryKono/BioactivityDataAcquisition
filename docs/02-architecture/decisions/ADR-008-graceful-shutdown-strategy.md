# ADR-008: Graceful Shutdown Strategy

*   **Status**: Accepted
*   **Date**: 2025-12-22
*   **Context**: ETL pipelines process large datasets in batches, maintaining state via checkpoints and holding distributed locks. An abrupt shutdown (kill -9, OOM, etc.) can leave the system in an inconsistent state: orphaned locks, missing checkpoints, partially written batches. A coordinated shutdown mechanism was needed to ensure data integrity.

## The Decision

We have implemented a **two-layer shutdown coordination system**:

1. **`ShutdownSignal`** (`application/core/shutdown.py`): Application-level signal object shared across components
2. **OS Signal Handlers** (`interfaces/orchestration/signals.py`): Translate SIGTERM/SIGINT to ShutdownSignal

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
│         setup_shutdown_handlers(shutdown_signal)             │
└─────────────────────────┬───────────────────────────────────┘
                          │ shutdown_signal.request()
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

| Layer | Responsibility |
|-------|----------------|
| interfaces | Captures OS signals, framework events |
| application | Coordinates shutdown via shared signal |
| infrastructure | Releases resources (locks, connections) |

This follows the hexagonal architecture: interfaces translate external events, application orchestrates, infrastructure cleans up.

### 2. Checkpoint-First Shutdown

On shutdown signal:
1. Current batch completes (no mid-batch abort)
2. Checkpoint is saved with last processed watermark
3. Lock heartbeat stops
4. Lock is released
5. Connections are closed

This ensures resumability—next run can continue from saved checkpoint.

### 3. Lock Safety Invariant

**Critical rule**: If lock is lost during shutdown, the pipeline MUST NOT write any data.

```python
# In executor
if shutdown_signal.is_requested:
    await checkpoint_manager.save()
    return  # Exit before next write

# Lock loss also triggers shutdown
if not await lock.is_held():
    shutdown_signal.request()
```

This prevents split-brain scenarios where multiple workers might write conflicting data.

### 4. Idempotent Shutdown

Multiple shutdown requests (e.g., SIGTERM followed by SIGINT) are handled gracefully:

```python
def request(self) -> None:
    if not self._requested:  # Only act once
        self._requested = True
        self._event.set()
```

## Implementation Details

### ShutdownSignal

```python
@dataclass
class ShutdownSignal:
    _requested: bool = field(default=False, init=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    @property
    def is_requested(self) -> bool:
        return self._requested

    def request(self) -> None:
        if not self._requested:
            self._requested = True
            self._event.set()

    async def wait(self) -> None:
        await self._event.wait()
```

### Signal Handler Setup

```python
def setup_shutdown_handlers(shutdown_signal: ShutdownSignal) -> None:
    def signal_handler(signum: int, _: Any) -> None:
        logger.warning(f"Received {signal.strsignal(signum)}, initiating shutdown")
        shutdown_signal.request()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
```

### Integration Points

```python
# Executor checks before each batch
async def execute(self, watermark, limit):
    for batch in self.fetch_batches():
        if self.shutdown_signal.is_requested:
            await self.save_checkpoint()
            break
        await self.process_batch(batch)

# Runner passes signal to all components
runner = PipelineRunner(
    shutdown_signal=shutdown_signal,
    executor=executor,
    ...
)
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
2. Checkpoint to be saved (~10s)
3. Lock release and cleanup (~5s)
4. Buffer for slow operations

## Related ADRs

- ADR-003: Redis for Distributed Locking (lock safety)
- ADR-007: Circuit Breaker Implementation (failure handling)
