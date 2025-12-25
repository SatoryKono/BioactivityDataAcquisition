# Pipeline Review Checklist

*Synced with RULES.md v5.0 (2025-12-15)*

Use this checklist when reviewing new or modified pipelines.

---

## 1. Architecture & Structure (RULES.md §1)

- [ ] Pipeline follows Ports & Adapters pattern
- [ ] Code located in `src/bioetl/application/pipelines/{provider}/{entity}/`
- [ ] Stage files present: `extract.py`, `transform.py`, `validate.py`, `export.py`
- [ ] Interfaces defined via `typing.Protocol` in `domain/ports/` package (import from facade)
- [ ] No I/O operations in domain layer

## 2. Configuration (RULES.md App D)

- [ ] Pipeline config exists at `configs/pipelines/{provider}/{entity}.yaml`
- [ ] Config includes required sections: `pipeline`, `source`, `sink`, `dq_rules`
- [ ] `circuit_breaker` and `rate_limit` parameters defined
- [ ] `load_strategy` specified (`incremental` | `full`)
- [ ] `forensic_retention` flag set for Critical tables if needed

## 3. Data Flow - Medallion Architecture (RULES.md §2.1)

### Bronze Layer

- [ ] Format: JSONL + zstd
- [ ] Path pattern: `bronze/{format_version}/{provider}/{entity}/{date}/`
- [ ] Append-only mode
- [ ] No in-place format migrations

### Silver Layer

- [ ] Format: Delta Lake (NOT raw Parquet)
- [ ] Mode: Merge/Upsert
- [ ] `primary_key` defined for deduplication
- [ ] `partition_by` specified

### Gold Layer

- [ ] Strict validation (`strict=True`)
- [ ] SCD Type 2 or partition overwrite strategy documented

## 4. Schema & Validation (RULES.md §2.2, §2.6)

- [ ] Pandera schema exists in `domain/schemas/{provider}/{entity}.py`
- [ ] Schema defines: columns, types, order, nullability
- [ ] Gold Data Contract published in `docs/contracts/gold/{entity}.json`
- [ ] Schema Drift handling configured (Info/Warn/Critical levels)
- [ ] Sentinel values NOT used (-1, "N/A", 9999)

## 5. Metadata & Lineage (RULES.md §2.3, §2.4)

- [ ] Records include `_run_id` (UUID)
- [ ] Records include `_run_type` (`incremental` | `backfill` | `rebuild`)
- [ ] Records include `_source_batch_id` (FK to lineage_log)
- [ ] Lineage recorded in `sys.lineage_log`
- [ ] Full Bronze paths NOT stored in each record

## 6. Content Hash / Entity ID (RULES.md §2.8)

- [ ] Entity ID strategy documented (source ID or content hash)
- [ ] Content Hash uses `sha256(provider + canonical_json(data))`
- [ ] Normalization applied before hashing:
  - [ ] NaN/Inf → null
  - [ ] Floats → round(10)
  - [ ] Dates → YYYY-MM-DD
  - [ ] Strings → strip()
- [ ] Meta-fields excluded from hash (`_ingestion_ts`, `_run_id`, etc.)

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
- [ ] Quarantine operations testable via `make quarantine-*`

## 9. Locking & Concurrency (RULES.md §3.3)

- [ ] Distributed lock implemented (Redis SETNX + EXPIRE)
- [ ] Lock key format: `lock:{provider}_{entity}`
- [ ] Backfill uses exclusive lock: `lock:{provider}_{entity}:exclusive`
- [ ] TTL: 60 seconds
- [ ] Heartbeat: every 20 seconds
- [ ] Fencing Token (`owner_id`) validated before write
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
  - [ ] `dq_validation_score`
  - [ ] `data_freshness_seconds`
- [ ] Provider health monitoring configured

## 11. Delta Maintenance (RULES.md §2.1.1)

- [ ] Weekly `VACUUM` scheduled with `retention_period=7 days`
- [ ] Forensic retention policy set appropriately (7d default; 30d for Critical tables via `forensic_retention: true`)

## 12. Security (RULES.md §5.2, §5.4)

- [ ] No hardcoded secrets
- [ ] Secrets via environment variables (`BIOETL_{PROVIDER}_{KEY}`)
- [ ] PII fields salted in Silver: `sha256(lowercase(value) + SALT)`
- [ ] PII excluded or aggregated in Gold
- [ ] No secrets in logs

## 13. Graceful Shutdown (RULES.md §5.3)

- [ ] SIGTERM/SIGINT handled
- [ ] Current batch completed before exit
- [ ] Checkpoint saved to S3 with ETag
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

- [ ] Pipeline docs in `docs/application/pipelines/{provider}/{entity}/`
- [ ] README with overview
- [ ] Schema documentation
- [ ] Error handling notes
- [ ] Runbook for common issues

## 16. Health Check (RULES.md App A)

- [ ] Health check endpoint configured
- [ ] Provider health states implemented:
  - [ ] Healthy: 0 errors in 5 min
  - [ ] Degraded: 1-2 errors → timeout×2, batch_size÷2
  - [ ] Unhealthy: ≥3 errors → pause, Alert P2

---

## Sign-off

| Role          | Name | Date | Approved |
|---------------|------|------|----------|
| Developer     |      |      | [ ]      |
| Reviewer      |      |      | [ ]      |
| Data Engineer |      |      | [ ]      |

---

## Notes

_Add any additional notes or exceptions here._
