# Quarantine Management

*Reference: [RULES.md §2.6](../../00-project/RULES.md#26-политика-null-и-пропущенных-значений)*

> Runtime profile: Local-Only single-instance (ADR-010). Quarantine operations are performed against local storage.

This runbook describes how to manage the Quarantine (Dead Letter Queue).

## Overview
Records that fail Data Quality (DQ) checks are sent to the Quarantine table (`common.quarantine`) instead of crashing the pipeline.

## Routine Tasks (Weekly)

### 1. Inspect Quarantine
Review new errors to identify systemic issues.
```bash
bioetl quarantine inspect --pipeline {pipeline-name} --limit 50
```

### 2. Triage Errors
- **Systemic Error**: Bug in parser or schema. -> **Fix Code**.
- **Data Error**: Source data is bad. -> **Contact Provider** or **Ignore**.
- **Transient Error**: Network glitch during validation. -> **Replay**.

### 3. Replay Records
After fixing a bug, replay quarantined records.
```bash
bioetl quarantine replay --pipeline {pipeline-name}
```
*Note: Replay targets records with `dq_status='NEW'` and marks processed records as `REPROCESSED`.*

### 4. Purge Garbage
Remove records that cannot be recovered.
```bash
bioetl quarantine purge --pipeline {pipeline-name}
```
*Note: Purge deletes old records from the Delta quarantine table.*

## Metrics
- `dq-records-quarantined-total`: Total records sent to quarantine.
- `dq-quarantine-size-bytes`: Storage size of quarantine table.

## Retention
Quarantine data is retained for **30 days** by default. Cleanup is executed via explicit purge operations (`bioetl quarantine purge`).
