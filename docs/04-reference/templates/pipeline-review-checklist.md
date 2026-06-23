______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Pipeline Review Checklist

*Synced with RULES.md v6.1 (2026-03-13)*

Use this checklist when reviewing new or modified pipelines.

______________________________________________________________________

## 1. Architecture & Structure (RULES.md §1)

- [ ] Pipeline follows Ports & Adapters pattern
- [ ] Transformer and provider-specific helpers located under `src/bioetl/application/pipelines/{provider}/`
- [ ] Pipeline exposes the current module layout (`{entity}_transformer.py` or `transformer.py`) instead of legacy stage files
- [ ] Pipeline registration/factory wiring updated for the new entity
- [ ] Interfaces defined via `typing.Protocol` in `domain/ports/` package (import from facade)
- [ ] No I/O operations in domain layer

## 2. Configuration (RULES.md App D)

- [ ] Pipeline config exists at `configs/entities/{provider}/{entity}.yaml`
- [ ] Unified config includes required sections: `pipeline`, `schema`, `quality`, `filters`, `contracts`
- [ ] Provider config exists at `configs/providers/{provider}.yaml` (source, rate-limit, circuit-breaker)
- [ ] `loading_strategy` specified (`full_scan_only` | `null`)
- [ ] `forensic-retention` flag set for Critical tables if needed

## 3. Data Flow - Medallion Architecture (RULES.md §2.1)

### Bronze Layer

- [ ] Format: JSONL + zstd
- [ ] Path pattern: `bronze/{format-version}/{provider}/{entity}/{date}/`
- [ ] Append-only mode
- [ ] No in-place format migrations

### Silver Layer

- [ ] Format: Delta Lake (NOT raw Parquet)
- [ ] Mode: Merge/Upsert
- [ ] `primary-key` defined for deduplication
- [ ] `partition-by` specified

### Gold Layer

- [ ] Strict validation (`strict=True`)
- [ ] SCD Type 2 or partition overwrite strategy documented

## 4. Schema & Validation (RULES.md §2.2, §2.6)

- [ ] Pandera schema exists in `domain/schemas/{provider}/{entity}.py`
- [ ] Schema defines: columns, types, order, nullability
- [ ] Gold Data Contract published in `docs/04-reference/contracts/gold/{provider}_{entity}_v{major}.{minor}.json`
- [ ] Schema Drift handling configured (Info/Warn/Critical levels)
- [ ] Sentinel values NOT used (-1, "N/A", 9999)

## 5. Metadata & Lineage (RULES.md §2.3, §2.4)

- [ ] Silver/Gold persisted rows do **not** include occurrence-scoped provenance
  such as `_run_id`, `_run_type`, `_source_batch_id`, or `_ingestion_ts`
- [ ] Occurrence-scoped provenance is published through metadata sidecars,
  lineage fragments, audit, run manifest, and run ledger
- [ ] Lineage recorded in metadata sidecar (`*_metadata.yaml`)
- [ ] Full Bronze paths NOT stored in each record

## 6. Content Hash / Entity ID (RULES.md §2.8)

- [ ] Entity ID strategy documented (source ID or content hash)
- [ ] Content Hash uses `sha256(provider + canonical-json(data))`
- [ ] Normalization applied before hashing:
  - [ ] NaN/Inf → null
  - [ ] Floats → round(10)
  - [ ] Dates → YYYY-MM-DD
  - [ ] Strings → strip()
- [ ] Occurrence-scoped provenance and DQ meta-fields excluded from semantic hash

## 7. Error Handling (RULES.md §3.1)

- [ ] Error classification implemented (Critical/Recoverable/DQ)
- [ ] DQ thresholds configured:
  - [ ] Soft: >5% → Warning
  - [ ] Hard: >20% → Fail Batch
- [ ] Retry strategy: Max 3 attempts, multiplier 2.0, jitter applied
- [ ] Circuit Breaker configured:
  - [ ] Trigger: 5 consecutive errors
  - [ ] Open Duration: 5 minutes
  - [ ] Recovery: Half-Open → probe request

## 8. Quarantine Integration (RULES.md §2.6)

- [ ] DQ failures routed to `common.quarantine`
- [ ] Quarantine record includes:
  - [ ] `ingestion_ts`
  - [ ] `pipeline`
  - [ ] `error_code`
  - [ ] `payload` (truncated to 64KB)
  - [ ] `bronze_batch_id`
  - [ ] `dq_status`
- [ ] Quarantine operations testable via `bioetl quarantine *`

## 9. Locking & Concurrency (RULES.md §3.3)

> **Note**: Local-Only Deployment (ADR-010). MemoryLock используется для локального развёртывания.

- [ ] Lock implemented (`MemoryLock` for Local-Only)
- [ ] Lock key format: `lock:{provider}-{entity}`
- [ ] Backfill uses exclusive lock: `lock:{provider}-{entity}:exclusive`
- [ ] Max Duration: 4 hours
- [ ] Safety Guard: lock validated before Delta write

## 10. Observability (RULES.md §3.2, §3.4)

- [ ] Structured JSON logging via `UnifiedLogger`
- [ ] Log schema compliance:
  - [ ] `ts` (MUST)
  - [ ] `level` (MUST)
  - [ ] `run_id` (MUST)
  - [ ] `pipeline` (MUST)
  - [ ] `stage` (MUST)
  - [ ] `dataset` (SHOULD)
  - [ ] `record_count` (SHOULD)
- [ ] DQ metrics exported (Prometheus format):
  - [ ] `dq-validation-score`
  - [ ] `data-freshness-seconds`
- [ ] Provider health monitoring configured

## 11. Delta Maintenance (RULES.md §2.1.1)

- [ ] Weekly `VACUUM` scheduled with `retention-period=7 days`
- [ ] Forensic retention policy set appropriately (7d default; 30d for Critical tables via `forensic-retention: true`)

## 12. Security (RULES.md §5.2, §5.4)

- [ ] No hardcoded secrets
- [ ] Secrets via environment variables (`BIOETL_{PROVIDER}_{KEY}`)
- [ ] PII fields salted in Silver: `sha256(lowercase(value) + SALT)`
- [ ] PII excluded or aggregated in Gold
- [ ] No secrets in logs

## 13. Graceful Shutdown (RULES.md §5.3)

- [ ] SIGTERM/SIGINT handled
- [ ] Current batch completed before exit
- [ ] Checkpoint saved to local storage (`data/output/checkpoints`)
- [ ] Lock released on exit
- [ ] Exit code 0 on success

## 14. Testing (RULES.md §4.2)

- [ ] Unit tests for domain logic (no network)
- [ ] Integration tests with VCR.py cassettes
- [ ] Cassettes sanitized (no secrets, no PII)
- [ ] Golden tests for output validation
- [ ] Coverage ≥80%
- [ ] Tests in `tests/` mirror `src/` structure

## 15. Documentation

- [ ] Provider reference doc exists in `docs/04-reference/providers/{provider}/{entity}.md`
- [ ] Detailed pipeline spec/xwalk docs updated in `docs/04-reference/pipelines/` when they exist for this entity
- [ ] README with overview
- [ ] Schema documentation
- [ ] Error handling notes
- [ ] Runbook for common issues

## 16. Health Check (RULES.md App A)

- [ ] Health check endpoint configured
- [ ] Provider health states implemented:
  - [ ] Healthy: 0 errors in 5 min
  - [ ] Degraded: 1-2 errors → timeout×2, batch-size÷2
  - [ ] Unhealthy: ≥3 errors → pause, Alert P2

## 17. Pre-flight Repository Hygiene

- [ ] `uv run python -m scripts.ops.data check-data-dir` проходит без ошибок
- [ ] Тяжёлые/временные локальные артефакты вынесены в `data/local/` или `tmp/`
- [ ] В релиз не попадают локальные артефакты (`data/local/**`, `tmp/**`)

______________________________________________________________________

## Sign-off

| Role          | Name | Date | Approved |
| ------------- | ---- | ---- | -------- |
| Developer     |      |      | [ ]      |
| Reviewer      |      |      | [ ]      |
| Data Engineer |      |      | [ ]      |

______________________________________________________________________

## Notes

-Add any additional notes or exceptions here.-
