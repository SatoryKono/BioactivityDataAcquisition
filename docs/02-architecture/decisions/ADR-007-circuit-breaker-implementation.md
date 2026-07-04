______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-007: Circuit Breaker Implementation

**Date:** 2025-12-22
**Status:** Accepted
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team

## Context

External API calls (ChEMBL, PubChem, UniProt) can experience temporary failures, slowdowns, or rate limiting. Without protection, the pipeline would repeatedly hammer failing services, wasting resources and potentially causing cascading failures. A circuit breaker pattern was needed to gracefully handle degraded external dependencies.

## Decision

We have implemented a **state machine-based Circuit Breaker** in `infrastructure/adapters/http/circuit_breaker.py` with the following characteristics:

1. **Three-state machine**: CLOSED → OPEN → HALF-OPEN → CLOSED
1. **Configurable thresholds**: `failure-threshold=5`, `recovery-timeout=300s`
1. **Selective triggering**: Only infrastructure errors (5xx, 429, timeouts) trip the breaker
1. **Thread-safe**: Uses `asyncio.Lock` for concurrent access

This decision implements RULES.md Section 3.1.4.

## State Machine

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
     ┌───────┐  failure-threshold  ┌──────┐      success
     │CLOSED │ ─────────────────▶ │ OPEN │ ──────────┐
     └───────┘                     └──────┘          │
         ▲                            │              │
         │                    recovery-timeout       │
         │                            │              │
         │                            ▼              │
         │                      ┌───────────┐        │
         └────── success ────── │ HALF-OPEN │ ───────┘
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

The HALF-OPEN state enables automatic recovery probing:

- After `recovery-timeout` (5 minutes), one probe request is allowed
- If successful, circuit closes and normal operation resumes
- If failed, circuit reopens for another timeout period

### 3. Selective Triggering

Not all errors should trip the circuit:

| Error Type         | Trips Circuit | Rationale                              |
| ------------------ | ------------- | -------------------------------------- |
| 5xx Server Error   | Yes           | Server-side issue, retrying won't help |
| 429 Rate Limit     | Yes           | Need to back off significantly         |
| Connection Timeout | Yes           | Network/server issue                   |
| 4xx Client Error   | No            | Client bug, fix code not circuit       |
| Validation Error   | No            | Data issue, not infrastructure         |

```python
def is-circuit-breaker-error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectError, ConnectTimeout, ReadTimeout)):
        return True
    if isinstance(exc, HTTPStatusError):
        return exc.response.status-code >= 500 or exc.response.status-code == 429
    return False
```

### 4. Metrics Integration

The circuit breaker exposes metrics for observability:

- `circuit-breaker-state{adapter}`: Current state (0=Closed, 1=Half-Open, 2=Open)
- `circuit-breaker-trips-total{adapter}`: Total OPEN transitions
- `circuit-breaker-success-total{adapter}`: Successful calls
- `circuit-breaker-failure-total{adapter}`: Failed calls

## Configuration

| Parameter           | Default | Description                         |
| ------------------- | ------- | ----------------------------------- |
| `failure-threshold` | 5       | Consecutive failures before opening |
| `recovery-timeout`  | 300s    | Time in OPEN before probing         |

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
from bioetl.infrastructure.adapters.http.circuit-breaker import CircuitBreaker

cb = CircuitBreaker(provider="chembl", failure-threshold=5)

async def fetch-activity(activity-id: int) -> dict:
    return await cb.call(http-client.get, f"/activity/{activity-id}")
```

## References

- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking (MemoryLock) — complementary resilience pattern (Updated: 2025-12-20)
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy — coordinates with circuit breaker during shutdown (Updated: 2025-12-22)
- [ADR-009](ADR-009-paginated-fetcher-mixin.md): PaginatedFetcherMixin — wraps fetch calls with circuit breaker (Updated: 2025-12-22)
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — circuit breaker is part of error handling (Updated: 2025-12-26)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                    |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-007-circuit-breaker-implementation.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                  |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                            |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`        |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                |

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
