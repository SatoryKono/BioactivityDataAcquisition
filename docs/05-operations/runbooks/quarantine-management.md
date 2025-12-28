# Quarantine Management

*Reference: [RULES.md §2.6](../../RULES.md#26-политика-null-и-пропущенных-значений)*

This runbook describes how to manage the Quarantine (Dead Letter Queue).

## Overview
Records that fail Data Quality (DQ) checks are sent to the Quarantine table (`common.quarantine`) instead of crashing the pipeline.

## Routine Tasks (Weekly)

### 1. Inspect Quarantine
Review new errors to identify systemic issues.
```bash
make quarantine-inspect PIPELINE={pipeline_name} LIMIT=50
```

### 2. Triage Errors
- **Systemic Error**: Bug in parser or schema. -> **Fix Code**.
- **Data Error**: Source data is bad. -> **Contact Provider** or **Ignore**.
- **Transient Error**: Network glitch during validation. -> **Replay**.

### 3. Replay Records
After fixing a bug, replay quarantined records.
```bash
make quarantine-replay PIPELINE={pipeline_name}
```
*Note: Only records with `dq_status='NEW'` are replayed.*

### 4. Purge Garbage
Remove records that cannot be recovered.
```bash
make quarantine-purge PIPELINE={pipeline_name}
```
*Note: This sets `dq_status='IGNORED'` (soft delete) or physically deletes depending on config.*

## Metrics
- `dq_records_quarantined_total`: Total records sent to quarantine.
- `dq_quarantine_size_bytes`: Storage size of quarantine table.

## Retention
Quarantine data is retained for **30 days** by default. Old records are automatically cleaned up.
