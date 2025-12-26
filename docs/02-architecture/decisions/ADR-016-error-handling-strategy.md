# ADR-016: Error Handling Strategy

*   **Status**: Accepted
*   **Date**: 2025-12-26
*   **Context**: The BioETL pipeline needs a consistent strategy for handling errors across all adapters and processing stages. Without a unified approach, error handling becomes fragmented, leading to inconsistent behavior, difficulty in debugging, and potential data loss.

## The Decision

We have implemented a **differentiated error handling strategy** with three tiers of classification, unified retry logic with deterministic jitter, Circuit Breaker pattern, and a Unified Quarantine mechanism.

### 1. Three-Tier Error Classification

| Error Type | Behavior | Examples |
|------------|----------|----------|
| **Critical** | Pipeline fail | Auth failure (401), schema mismatch in Gold, database unavailable |
| **Recoverable** | Retry with backoff (max 3 attempts) | 429 Rate Limit, 502/504 Timeout, network errors |
| **Data Quality** | Log + skip record | Invalid SMILES, missing optional field |

This decision implements RULES.md Section 3.1.

### 2. Exponential Backoff with Deterministic Jitter

```python
# RetryConfig parameters
max_attempts: 3
multiplier: 2.0        # wait 1s, 2s, 4s...
jitter: (0.1s, 0.5s)   # random range

# Deterministic mode (for reproducibility)
deterministic: True    # Hash-based jitter instead of random
jitter_seed: 42        # Optional seed for reproducibility
```

**Deterministic Jitter Calculation:**
```python
hash_input = f"{attempt}:{url}:{seed}"
jitter_factor = (hash(hash_input) % 1000) / 1000.0
jitter = jitter_min + jitter_factor * (jitter_max - jitter_min)
```

### 3. Circuit Breaker

State machine pattern for cascading failure protection:

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

**Configuration:**
- `failure_threshold`: 5 consecutive errors
- `recovery_timeout`: 300s (5 minutes)
- Triggering errors: 5xx, 429, connection timeouts

See [ADR-007](ADR-007-circuit-breaker-implementation.md) for implementation details.

### 4. Unified Quarantine with 64KB Truncation

All failed records are stored in a single quarantine table `common.quarantine`:

| Field | Type | Description |
|-------|------|-------------|
| `ingestion_ts` | Timestamp | Time of incident |
| `pipeline` | String | Pipeline name (e.g., `chembl_activity`) |
| `error_code` | String | Error type (e.g., `SCHEMA_VIOLATION`) |
| `payload` | JSON/Text | Raw record (**truncated to 64KB**) |
| `payload_hash` | String | SHA256 for deduplication |
| `bronze_batch_id` | UUID | Reference to source batch |
| `dq_status` | String | `NEW` \| `IGNORED` \| `REPROCESSED` |

**64KB Truncation Rationale:**
- Prevents storage bloat from large malformed records
- Maintains linkage to Bronze via `bronze_batch_id` for full payload access
- Sufficient context for debugging most issues

### 5. Batch Error Thresholds

| Threshold | Condition | Action |
|-----------|-----------|--------|
| **Soft** | >5% DQ errors | Warning |
| **Hard** | >20% DQ errors | Fail Batch |

Metrics tracked:
- `record_error_rate`: Ratio of bad rows
- `entity_error_rate`: Ratio of bad unique entities

## Justification

### 1. Differentiated Handling Prevents Over-Engineering

Not all errors deserve the same treatment:
- Critical errors need immediate attention
- Recoverable errors should be retried automatically
- Data quality issues shouldn't stop the pipeline

### 2. Deterministic Jitter Enables Reproducibility

Per [ADR-014](ADR-014-deterministic-writes.md), infrastructure must be deterministic:
- Hash-based jitter allows reproducible retries in tests
- Random jitter still used in production for thundering herd prevention
- Configurable via `RetryConfig(deterministic=True)`

### 3. Unified Quarantine Simplifies Operations

Instead of per-pipeline quarantine tables:
- Single location for all failed records
- Consistent schema for tooling
- Cross-pipeline analysis capability
- Simpler retention management

### 4. Circuit Breaker Prevents Cascading Failures

When external APIs fail:
- Stops hammering failing services
- Preserves rate limit quotas
- Enables graceful degradation
- Automatic recovery via half-open probing

## Implementation Details

### Error Classification

```python
from bioetl.domain.exceptions import (
    CriticalPipelineError,   # Stops pipeline
    RecoverableError,         # Retry with backoff
    DataQualityError,         # Log and skip
)

def handle_error(error: Exception) -> None:
    if isinstance(error, CriticalPipelineError):
        raise  # Pipeline fails
    elif isinstance(error, RecoverableError):
        # Retry logic handles this
        pass
    elif isinstance(error, DataQualityError):
        quarantine.write(
            pipeline=context.pipeline_name,
            error_code=error.code,
            payload=error.record,
            bronze_batch_id=batch_id,
            ingestion_ts=context.started_at,
        )
```

### Circuit Breaker Usage

```python
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    CircuitBreaker,
    is_circuit_breaker_error,
)

cb = CircuitBreaker(provider="chembl", failure_threshold=5)

async def fetch_with_protection(url: str) -> dict:
    return await cb.call(http_client.get, url)
```

### Quarantine Port

```python
class QuarantinePort(Protocol):
    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None: ...

    async def inspect(
        self,
        pipeline: str,
        limit: int = 10,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get_stats(self, pipeline: str) -> dict[str, Any]: ...
```

## Alternatives Considered

### 1. Fail-Fast Only

Rejected because:
- Wastes resources on transient failures
- Doesn't distinguish data quality from infrastructure issues
- Poor user experience for minor issues

### 2. Per-Pipeline Quarantine Tables

Rejected because:
- Schema duplication
- Tooling complexity
- Cross-pipeline analysis difficult
- Higher storage overhead

### 3. Unlimited Payload in Quarantine

Rejected because:
- Storage cost explosion with malformed large records
- 64KB covers 99% of debugging needs
- Full payload accessible via Bronze linkage

### 4. No Deterministic Mode

Rejected because:
- Tests become non-reproducible
- Debugging retry issues is difficult
- Violates [ADR-014](ADR-014-deterministic-writes.md) principles

## Consequences

### Positive

- **Consistent behavior** across all pipelines
- **Graceful degradation** instead of hard failures
- **Reproducible retries** in deterministic mode
- **Unified operations** via single quarantine table
- **Cost control** via payload truncation

### Negative

- **Complexity**: Three error types require understanding
- **Truncation risk**: Very large records lose data in quarantine (mitigated by Bronze linkage)
- **Circuit breaker scope**: Per-provider, not per-endpoint (acceptable tradeoff)

## Related ADRs

- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes and Retries
