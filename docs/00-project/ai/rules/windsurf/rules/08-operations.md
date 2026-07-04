---
trigger: glob
description: "BioETL operations — secrets, locks, shutdown, local-only runtime"
globs:
  - "configs/**/*.yaml"
  - "src/**/*.py"
---

# Operations (Local-Only)

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

## Secrets (MUST)

- Source: `os.environ` only; format `BIOETL_{PROVIDER}_{KEY}`
- Hardcoded secrets and committed `.env` **MUST NOT**
- Least privilege for secrets and `data/output` write paths
- `.env` edits require explicit per-task user approval (see `05-agent-workflow`)

## Locks (MemoryLock only — ADR-010)

| Parameter | Value |
| --------- | ----- |
| Mechanism | `MemoryLock` (in-process, Local-Only) |
| TTL | 90s (`heartbeat-interval * 3`) |
| Heartbeat | 30s |
| Max duration | 4h forced release |
| Fencing token | owner = run_id |

- Incremental: `lock:{provider}-{entity}`
- Backfill/rebuild exclusive: `lock:{provider}-{entity}:exclusive`
- `--wait-for-lock` default timeout: **300s**
- Redis/distributed locks **MUST NOT**
- Lock loss = loss of write rights; validate owner immediately before commit
- Cleanup/release lock idempotent in finally

## Backfill / Rebuild vs Incremental

| run_type | Behavior |
| -------- | -------- |
| `backfill` / `rebuild` | Exclusive lock; `clear_silver()` + `clear_gold()` (if configured) before execute; no parallel runs per entity |
| `incremental` | **MUST NOT** call `clear_silver()` or `clear_gold()` |

- `_run_type` published in control plane — **MUST NOT** appear in physical Delta merge predicate
- `run_type`: `incremental` | `backfill` | `rebuild`

## Checkpoint & Resume

- Checkpoint written **only after** durable commit boundary
- On startup: check checkpoint; `--resume` → `last_processed_id + 1`; without flag → warning on stale checkpoint
- Success → delete checkpoint; atomic write (`*.tmp` → rename)
- `loading_strategy: full_scan_only` → checkpoint resume **MUST NOT** (publication configs must set explicitly)

## Graceful Shutdown (SIGTERM/SIGINT)

1. Stop fetching new records
2. Finish current batch write
3. Save checkpoint atomically
4. Release resources and lock
5. Exit code **0**; record SHUTDOWN terminal state

All adapters/services: idempotent `async def aclose()` (no exceptions). `PipelineService`: async context manager.

## Rate Limiting

Each HTTP adapter **MUST** use `TokenBucket` (or equivalent).
Backpressure when internal queue **>80%** full.

## Environment Isolation

- Separate data roots per profile (`data/dev`, staging-like, prod-like local)
- MemoryLock scoped by working directory/environment
- Live credentials **MUST NOT** in repository or published docs
- BioETL **local-only by default** — no Docker/Redis unless task requires ADR

## Disaster Recovery

| Metric | Target |
| ------ | ------ |
| RPO | 24 hours |
| RTO | 4 hours |

- Time Travel is operational, not full DR substitute
- Restore drills SHOULD be documented (DR Game Day per RULES)
- **No automatic application rollback** in Local-Only runtime — manual procedure only
- DQ errors **MUST NOT** trigger automatic version rollback

## Security Summary

- Silver PII: salted deterministic hash; Gold: exclude or aggregate
- Redact secrets/Authorization/PII from logs, traces, exceptions, VCR cassettes
- Dependencies: version ranges in `pyproject.toml` + committed `uv.lock`
