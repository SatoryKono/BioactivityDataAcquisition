______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-016: Error Handling Strategy

**Date:** 2025-12-26
**Status:** Accepted
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team

## Context

The BioETL pipeline needs a consistent strategy for handling errors across all adapters and processing stages. Without a unified approach, error handling becomes fragmented, leading to inconsistent behavior, difficulty in debugging, and potential data loss.

## Decision

We have implemented a **differentiated error handling strategy** with three tiers of classification, unified retry logic with deterministic jitter, Circuit Breaker pattern, and a Unified Quarantine mechanism.

### 1. Three-Tier Error Classification

| Error Type       | Behavior                            | Examples                                                          |
| ---------------- | ----------------------------------- | ----------------------------------------------------------------- |
| **Critical**     | Pipeline fail                       | Auth failure (401), schema mismatch in Gold, database unavailable |
| **Recoverable**  | Retry with backoff (max 3 attempts) | 429 Rate Limit, 502/504 Timeout, network errors                   |
| **Data Quality** | Log + skip record                   | Invalid SMILES, missing optional field                            |

This decision implements RULES.md Section 3.1.

### 2. Exponential Backoff with Deterministic Jitter

```python
# RetryConfig parameters
max-attempts: 3
multiplier: 2.0        # wait 1s, 2s, 4s...
jitter: (0.1s, 0.5s)   # random range

# Deterministic mode (for reproducibility)
deterministic: True    # Hash-based jitter instead of random
jitter-seed: 42        # Optional seed for reproducibility
```

**Deterministic Jitter Calculation:**

```python
hash - input = f"{attempt}:{url}:{seed}"
jitter - factor = (hash(hash - input) % 1000) / 1000.0
jitter = jitter - min + jitter - factor * (jitter - max - jitter - min)
```

### 3. Circuit Breaker

State machine pattern for cascading failure protection:

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

**Configuration:**

- `failure-threshold`: 5 consecutive errors
- `recovery-timeout`: 300s (5 minutes)
- Triggering errors: 5xx, 429, connection timeouts

See [ADR-007](ADR-007-circuit-breaker-implementation.md) for implementation details.

### 4. Unified Quarantine with 64KB Truncation

All failed records are stored in a single quarantine table `common.quarantine`:

| Field             | Type      | Description                             |
| ----------------- | --------- | --------------------------------------- |
| `ingestion_ts`    | Timestamp | Time of incident                        |
| `pipeline`        | String    | Pipeline name (e.g., `chembl_activity`) |
| `error-code`      | String    | Error type (e.g., `SCHEMA-VIOLATION`)   |
| `payload`         | JSON/Text | Raw record (**truncated to 64KB**)      |
| `payload-hash`    | String    | SHA256 for deduplication                |
| `bronze-batch-id` | UUID      | Reference to source batch               |
| `dq-status`       | String    | `NEW` \| `IGNORED` \| `REPROCESSED`     |

**64KB Truncation Rationale:**

- Prevents storage bloat from large malformed records
- Maintains linkage to Bronze via `bronze-batch-id` for full payload access
- Sufficient context for debugging most issues

### 5. Batch Error Thresholds

| Threshold | Condition      | Action     |
| --------- | -------------- | ---------- |
| **Soft**  | >5% DQ errors  | Warning    |
| **Hard**  | >20% DQ errors | Fail Batch |

Metrics tracked:

- `record-error-rate`: Ratio of bad rows
- `entity-error-rate`: Ratio of bad unique entities

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

def handle-error(error: Exception) -> None:
    if isinstance(error, CriticalPipelineError):
        raise  # Pipeline fails
    elif isinstance(error, RecoverableError):
        # Retry logic handles this
        pass
    elif isinstance(error, DataQualityError):
        quarantine.write(
            pipeline=context.pipeline-name,
            error-code=error.code,
            payload=error.record,
            bronze-batch-id=batch-id,
            ingestion_ts=context.started_at,
        )
```

### Circuit Breaker Usage

```python
from bioetl.infrastructure.adapters.http.circuit-breaker import (
    CircuitBreaker,
    is-circuit-breaker-error,
)

cb = CircuitBreaker(provider="chembl", failure-threshold=5)

async def fetch-with-protection(url: str) -> dict:
    return await cb.call(http-client.get, url)
```

### Quarantine Port

```python
class QuarantinePort(Protocol):
    async def write(
        self,
        pipeline: str,
        error-code: str,
        payload: dict[str, Any],
        bronze-batch-id: BatchID,
        run-id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None: ...

    async def inspect(
        self,
        pipeline: str,
        limit: int = 10,
        error-code: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get-stats(self, pipeline: str) -> dict[str, Any]: ...
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

## References

- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation (Updated: 2025-12-22)
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy (Updated: 2025-12-22)
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes and Retries (Updated: 2025-12-24)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-016-error-handling-strategy.md` |
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
