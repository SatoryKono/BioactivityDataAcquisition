# DQ Failure Investigation Runbook

*Reference: [RULES.md §3.1.2](../../00-project/RULES.md#312-пороги-ошибок-батча-thresholds)*

> Runtime profile: Local-Only single-instance (ADR-010). DQ investigation operates on local Silver/Gold/Quarantine artifacts.

## Overview

Data Quality (DQ) checks ensure data integrity throughout the pipeline. This runbook covers investigating DQ threshold violations and data quality issues.

## DQ Thresholds

| Threshold | Default | Behavior                                              |
| --------- | ------- | ----------------------------------------------------- |
| Soft      | 5%      | Warning logged, pipeline continues                    |
| Hard      | 20%     | Pipeline fails with exit code 83 (DATA-QUALITY-ERROR) |

Configuration:

```yaml
# configs/entities/chembl/activity.yaml
dq:
  soft-fail-threshold: 0.05  # 5%
  hard-fail-threshold: 0.20  # 20%
```

## Symptoms

- Pipeline exits with code 83 (DATA-QUALITY-ERROR, DQ hard threshold)
- Log messages: `dq-soft-threshold-exceeded`
- Prometheus metric: `bioetl-dq-soft-threshold-exceeded-total`
- Records in quarantine directory

## Investigation Steps

### Step 1: Identify Failure Scope

Check logs for DQ summary:

```bash
grep "dq-check\|dq-threshold" logs/bioetl.log | tail -20
```

Key log fields:

- `dq-error-rate`: Percentage of failed records
- `dq-errors-total`: Absolute count
- `dq-records-processed`: Total records in batch
- `validation-errors`: Types of failures

### Step 2: Examine Quarantine Records

Quarantined records are stored in unified Delta table:

```
data/output/quarantine
```

```bash
# Inspect recent records for one pipeline
bioetl quarantine inspect --pipeline chembl_activity --limit 10
```

Quarantine record structure:

```json
{
  "pipeline": "chembl_activity",
  "dq_status": "NEW",
  "error_code": "VALIDATION_ERROR",
  "ingestion_ts": "2026-01-02T14:30:00Z",
  "payload_hash": "<hash>"
}
```

### Step 3: Categorize Errors

Common DQ error categories:

| Category        | Examples                 | Severity |
| --------------- | ------------------------ | -------- |
| Missing fields  | `null` in required field | Medium   |
| Invalid format  | Bad SMILES, invalid date | High     |
| Out of range    | Negative IC50, >1M MW    | Medium   |
| Type mismatch   | String in numeric field  | High     |
| Encoding issues | Invalid UTF-8            | Low      |

```python
# CLI dashboard
# (includes by_error_code/by_status and oldest/newest timestamps)
bioetl quarantine stats --pipeline chembl_activity
```

### Step 4: Root Cause Analysis

**Source Data Issues**

- Check if upstream API changed response format
- Verify API version in use
- Compare with known-good historical data

**Schema Evolution**

- Check if new fields were added upstream
- Verify transformer handles optional fields
- Review schema validation rules

**Pipeline Bug**

- Review recent code changes to transformer
- Check for off-by-one errors in parsing
- Verify type coercion logic

### Step 5: Impact Assessment

```python
from deltalake import DeltaTable
import polars as pl

# Check current Silver table state
dt = DeltaTable("data/output/silver/chembl/activity")
df = pl.scan-delta(str(dt)).collect()

# Count records by run_id
run-stats = df.group-by("_run_id").agg(
    [
        pl.count().alias("records"),
        pl.col("_dq_passed").sum().alias("passed"),
    ]
)
print(run-stats)
```

## Resolution Procedures

### Option 1: Fix and Reprocess Quarantine

For fixable issues (e.g., encoding, format):

```python
import json
from pathlib import Path


def reprocess-quarantine(quarantine-dir: str, output-file: str):
    """Extract and fix quarantined records."""
    fixed-records = []

    for f in Path(quarantine-dir).glob("*.jsonl"):
        for line in f.read-text().splitlines():
            record = json.loads(line)
            original = record["original-record"]

            # Apply fixes based on error type
            if record["error-type"] == "encoding-error":
                # Fix encoding
                original["field"] = original["field"].encode("utf-8", "ignore").decode()
                fixed-records.append(original)

    with open(output-file, "w") as f:
        for record in fixed-records:
            f.write(json.dumps(record) + "\n")

    print(f"Fixed {len(fixed-records)} records")
```

### Option 2: Adjust Thresholds

If DQ issues are expected (e.g., known data quality in source):

```yaml
# Temporarily relax thresholds
dq:
  soft-fail-threshold: 0.10  # 10%
  hard-fail-threshold: 0.30  # 30%
```

**Warning**: Document why thresholds were changed!

### Option 3: Add Data Cleansing

For systematic issues, add cleansing to transformer:

```python
def transform(self, record: dict) -> dict:
    # Existing transformation

    # Add cleansing for known issues
    if record.get("canonical-smiles") == "":
        record["canonical-smiles"] = None

    if record.get("molecular-weight", 0) < 0:
        record["molecular-weight"] = None

    return record
```

### Option 4: Skip Problematic Records

For unfixable records, quarantine is the correct behavior:

```bash
# View quarantine statistics
bioetl quarantine stats --pipeline chembl_activity

# Purge old quarantine (> 30 days)
bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
```

## Prevention

### Add Schema Tests

```python
# tests/unit/test-chembl-schema.py
def test-activity-schema-handles-null-smiles():
    record = {"activity-id": 1, "canonical-smiles": None}
    result = transform(record)
    assert result["canonical-smiles"] is None
```

### Monitor DQ Trends

Set up dashboards for:

- DQ error rate over time
- Error type distribution
- Records quarantined per run

Alert on:

- Soft threshold exceeded
- New error type appearing
- Sudden spike in quarantine rate

### Document Known Issues

Maintain a list of known DQ issues:

```markdown
# Known DQ Issues

| Provider | Entity | Issue | Workaround | Status |
|----------|--------|-------|------------|--------|
| ChEMBL | activity | Empty SMILES | Treat as null | Accepted |
| PubChem | compound | Invalid InChI | Skip record | Investigating |
```

## Metrics

Key Prometheus metrics:

- `bioetl-dq-records-processed-total{provider, entity}`
- `bioetl-dq-records-passed-total{provider, entity}`
- `bioetl-dq-records-failed-total{provider, entity}`
- `bioetl-dq-soft-threshold-exceeded-total{provider, entity}`
- `bioetl-dq-check-duration-ms{provider, entity}`

## Escalation

Escalate if:

- Hard threshold exceeded for > 3 consecutive runs
- Error rate increasing over time
- New error type not in known issues
- Upstream API changes suspected
