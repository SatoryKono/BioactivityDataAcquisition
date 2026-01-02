# ADR-007: Circuit Breaker Implementation

*   **Status**: Accepted
*   **Date**: 2025-12-22
*   **Last Updated**: 2026-01-02
*   **Context**: External API calls (ChEMBL, PubChem, UniProt) can experience temporary failures, slowdowns, or rate limiting. Without protection, the pipeline would repeatedly hammer failing services, wasting resources and potentially causing cascading failures. A circuit breaker pattern was needed to gracefully handle degraded external dependencies.

## The Decision

We have implemented a **state machine-based Circuit Breaker** in `infrastructure/adapters/http/circuit_breaker.py` with the following characteristics:

1. **Three-state machine**: CLOSED → OPEN → HALF_OPEN → CLOSED
2. **Configurable thresholds**: `failure_threshold=5`, `recovery_timeout=300s`
3. **Selective triggering**: Only infrastructure errors (5xx, 429, timeouts) trip the breaker
4. **Thread-safe**: Uses `asyncio.Lock` for concurrent access

This decision implements RULES.md Section 3.1.4.

## State Machine

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
     ┌───────┐  failure_threshold  ┌──────┐      success
     │CLOSED │ ─────────────────▶ │ OPEN │ ──────────┐
     └───────┘                     └──────┘          │
         ▲                            │              │
         │                    recovery_timeout       │
         │                            │              │
         │                            ▼              │
         │                      ┌───────────┐        │
         └────── success ────── │ HALF_OPEN │ ───────┘
                                └───────────┘
                                      │
                                   failure
                                      │
                                      ▼
                                  ┌──────┐
                                  │ OPEN │
                                  └──────┘
```

## Justification

### 1. Fail-Fast Principle

When a service is down, continuing to retry wastes:
- Network bandwidth
- API rate limits
- Processing time
- Memory for pending requests

The circuit breaker allows immediate failure with `CircuitBreakerOpenError`, letting the pipeline checkpoint and wait.

### 2. Self-Healing

The HALF_OPEN state enables automatic recovery probing:
- After `recovery_timeout` (5 minutes), one probe request is allowed
- If successful, circuit closes and normal operation resumes
- If failed, circuit reopens for another timeout period

### 3. Selective Triggering

Not all errors should trip the circuit:

| Error Type | Trips Circuit | Rationale |
|------------|---------------|-----------|
| 5xx Server Error | Yes | Server-side issue, retrying won't help |
| 429 Rate Limit | Yes | Need to back off significantly |
| Connection Timeout | Yes | Network/server issue |
| 4xx Client Error | No | Client bug, fix code not circuit |
| Validation Error | No | Data issue, not infrastructure |

```python
def is_circuit_breaker_error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectError, ConnectTimeout, ReadTimeout)):
        return True
    if isinstance(exc, HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return False
```

### 4. Metrics Integration

The circuit breaker exposes metrics for observability:
- `circuit_breaker_state{provider}`: Current state (0=Closed, 1=Half-Open, 2=Open)
- `circuit_breaker_trips_total{provider}`: Total OPEN transitions

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Consecutive failures before opening |
| `recovery_timeout` | 300s | Time in OPEN before probing |

These defaults balance between:
- **Too sensitive** (threshold=1): Normal transient failures trip circuit
- **Too tolerant** (threshold=20): Wastes resources on prolonged outages
- **Too short recovery** (10s): Hammers service during partial outages
- **Too long recovery** (1h): Slow recovery after transient issues

## Alternatives Considered

### 1. Simple Retry with Backoff Only

Rejected because:
- Doesn't prevent hammering during prolonged outages
- No state awareness across requests
- Memory waste from queued retries

### 2. External Service (Resilience4j, Polly via sidecar)

Rejected because:
- Adds infrastructure dependency
- Overkill for single-service CLI tool
- Language boundary complexity

### 3. Rolling Window (failures in last N seconds)

Considered but deferred:
- More complex implementation
- Current consecutive-failures approach works well for API patterns
- Can be added later if needed

## Consequences

### Positive
- Prevents cascading failures during API outages
- Automatic recovery without manual intervention
- Observable via metrics
- Thread-safe for concurrent requests

### Negative
- **Single circuit per provider**: All endpoints share one circuit. If `/compound` fails but `/activity` works, both are blocked. Acceptable tradeoff for simplicity.
- **No persistent state**: Circuit resets on process restart. Acceptable for batch pipelines.

## Usage Example

```python
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

cb = CircuitBreaker(provider="chembl", failure_threshold=5)

async def fetch_activity(activity_id: int) -> dict:
    return await cb.call(http_client.get, f"/activity/{activity_id}")
```

## Related ADRs

- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking (MemoryLock) — complementary resilience pattern (Updated: 2025-12-20)
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy — coordinates with circuit breaker during shutdown (Updated: 2025-12-22)
- [ADR-009](ADR-009-paginated-fetcher-mixin.md): PaginatedFetcherMixin — wraps fetch calls with circuit breaker (Updated: 2025-12-22)
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — circuit breaker is part of error handling (Updated: 2025-12-26)
