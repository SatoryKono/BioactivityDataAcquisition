---
trigger: model_decision
description: "BioETL Patterns — Adapters, Pipelines, Composites"
---

# HTTP Transport (ADR-032)

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

- **Canonical client:** `UnifiedHTTPClient` in `bioetl.infrastructure.adapters.http.client`
- **MUST NOT:** create parallel `UnifiedAPIClient`, use direct `requests`, or raw `httpx` outside approved infrastructure contour
- Controlled rename requires ADR + migration + removal of superseded implementation
- Async HTTP via `httpx` inside approved client; blocking legacy libs via `BaseSyncAdapter` / executor

Each provider adapter **MUST** have: retry policy, bounded backoff, rate limiting, timeout, pagination, health check, 4xx/5xx classification, Retry-After handling.

## Creating HTTP Adapter

```python
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class NewAdapter(BaseHttpAdapter):
    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort):
        super().__init__(http_client, logger)
        self.provider_name = "new-provider"
```

## UnifiedHTTPClient Components

- **TokenBucket**: per-provider rate limiting; backpressure when queue >80%
- **Circuit Breaker**: 5 consecutive connection/timeout errors → open 5 min; half-open 1 probe; alert if open >10 min
- **Retry**: max 3, multiplier 2.0; jitter 0.1–0.5s SHOULD (deterministic mode via hash when `RetryConfig(deterministic=True)`)
- **Metrics**: via `MetricsPort` (`bioetl_` prefix, bounded labels)

## Provider Health States

| State | Trigger | Behavior |
| ----- | ------- | -------- |
| DEGRADED | 1–2 consecutive errors | timeout ×2, batch size ÷2 |
| UNHEALTHY | ≥3 errors | pause pipeline, P2 alert |
| Metric | `provider-health-status` | 0=Unhealthy, 1=Degraded, 2=Healthy |

Non-retriable auth/validation errors fail immediately; 429/502/504/selected 5xx retry within policy.

## Creating Sync Adapter (Legacy)

```python
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

class LegacyAdapter(BaseSyncAdapter):
    provider_name = "legacy"
    # _run_in_executor for sync libs — must not block event loop
```

# Composite Pipelines (ADR-026)

**Mandatory stage order:** Seed → Dependencies → Enrichers → Merge → Cross-validation → Gold write.

| Stage | Rules |
| ----- | ----- |
| Seed | Primary entity, business identity, output keys |
| Dependencies | Full API → Bronze → Silver lifecycle after seed, before enrichers |
| Enrichers | `join_keys ⊆ seed.output_keys`; empty/missing join key rejected pre-execution |
| Merge | Deterministic; strategy + conflict resolution via approved enums |
| Cross-validation | Before Gold write; bounded `_cv_*` metadata only |

**Merge config:**
```yaml
merge:
  strategy: left_outer | inner | union
  conflict_resolution: seed_priority | enricher_priority | coalesce | explicit_rules
  preserve_all_sources: true | false
  field_priorities: ...  # required for EXPLICIT_RULES
```

- `MANY_TO_ONE` requires explicit aggregation config — implicit first/last forbidden
- `preserve_all_sources=true` → qualified `provider.entity.field`; else coalesce by priority
- Field group **TRASH** excluded from Gold; `gold.rename_fields` applies to normalized Silver column names
- Optional enricher failure follows explicit fallback; required component failure stops run
- Cross-validation may nullify only fields of failing enricher on proven `ENRICHER_ERROR`

# Configuration Location

Unified format: `configs/entities/{provider}/{entity}.yaml`

Contains: pipeline, schema, quality, filters, contracts, hash-policy, write modes, idempotency contract (when Silver APPEND).

# Idempotency

Retries, pagination, restart, and replay must not create duplicate persisted semantic rows. Delivery: at-least-once transport + deterministic dedup/merge.
