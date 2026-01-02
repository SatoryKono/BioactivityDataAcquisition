# DQ Failure Investigation Runbook

## Overview

Data Quality (DQ) checks ensure data integrity throughout the pipeline. This runbook covers investigating DQ threshold violations and data quality issues.

## DQ Thresholds

| Threshold | Default | Behavior |
|-----------|---------|----------|
| Soft | 5% | Warning logged, pipeline continues |
| Hard | 20% | Pipeline fails with exit code 10 |

Configuration:
```yaml
# configs/pipelines/chembl/activity.yaml
dq:
  soft_fail_threshold: 0.05  # 5%
  hard_fail_threshold: 0.20  # 20%
```

## Symptoms

- Pipeline exits with code 10 (DQ hard threshold)
- Log messages: `dq_soft_threshold_exceeded`
- Prometheus metric: `bioetl_dq_soft_threshold_exceeded_total`
- Records in quarantine directory

## Investigation Steps

### Step 1: Identify Failure Scope

Check logs for DQ summary:
```bash
grep "dq_check\|dq_threshold" logs/bioetl.log | tail -20
```

Key log fields:
- `dq_error_rate`: Percentage of failed records
- `dq_errors_total`: Absolute count
- `dq_records_processed`: Total records in batch
- `validation_errors`: Types of failures

### Step 2: Examine Quarantine Records

Quarantined records are stored in:
```
data/quarantine/{provider}/{entity}/{date}/
```

```bash
# List quarantine files
ls -la data/quarantine/chembl/activity/

# View recent quarantine records
cat data/quarantine/chembl/activity/2026-01-02/*.jsonl | head -10 | jq
```

Quarantine record structure:
```json
{
  "original_record": { ... },
  "error_type": "validation_error",
  "error_message": "Invalid SMILES: 'XYZ'",
  "field": "canonical_smiles",
  "quarantine_timestamp": "2026-01-02T14:30:00Z",
  "run_id": "run-20260102-143022-abc123"
}
```

### Step 3: Categorize Errors

Common DQ error categories:

| Category | Examples | Severity |
|----------|----------|----------|
| Missing fields | `null` in required field | Medium |
| Invalid format | Bad SMILES, invalid date | High |
| Out of range | Negative IC50, >1M MW | Medium |
| Type mismatch | String in numeric field | High |
| Encoding issues | Invalid UTF-8 | Low |

```python
import json
from collections import Counter
from pathlib import Path

# Count error types
error_types = Counter()
quarantine_dir = Path("data/quarantine/chembl/activity/2026-01-02")

for f in quarantine_dir.glob("*.jsonl"):
    for line in f.read_text().splitlines():
        record = json.loads(line)
        error_types[record.get("error_type", "unknown")] += 1

print("Error distribution:")
for error, count in error_types.most_common():
    print(f"  {error}: {count}")
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
dt = DeltaTable("data/silver/chembl_activity")
df = pl.scan_delta(str(dt)).collect()

# Count records by run_id
run_stats = df.group_by("_run_id").agg([
    pl.count().alias("records"),
    pl.col("_dq_passed").sum().alias("passed"),
])
print(run_stats)
```

## Resolution Procedures

### Option 1: Fix and Reprocess Quarantine

For fixable issues (e.g., encoding, format):

```python
import json
from pathlib import Path

def reprocess_quarantine(quarantine_dir: str, output_file: str):
    """Extract and fix quarantined records."""
    fixed_records = []

    for f in Path(quarantine_dir).glob("*.jsonl"):
        for line in f.read_text().splitlines():
            record = json.loads(line)
            original = record["original_record"]

            # Apply fixes based on error type
            if record["error_type"] == "encoding_error":
                # Fix encoding
                original["field"] = original["field"].encode('utf-8', 'ignore').decode()
                fixed_records.append(original)

    with open(output_file, "w") as f:
        for record in fixed_records:
            f.write(json.dumps(record) + "\n")

    print(f"Fixed {len(fixed_records)} records")
```

### Option 2: Adjust Thresholds

If DQ issues are expected (e.g., known data quality in source):

```yaml
# Temporarily relax thresholds
dq:
  soft_fail_threshold: 0.10  # 10%
  hard_fail_threshold: 0.30  # 30%
```

**Warning**: Document why thresholds were changed!

### Option 3: Add Data Cleansing

For systematic issues, add cleansing to transformer:

```python
def transform(self, record: dict) -> dict:
    # Existing transformation

    # Add cleansing for known issues
    if record.get("canonical_smiles") == "":
        record["canonical_smiles"] = None

    if record.get("molecular_weight", 0) < 0:
        record["molecular_weight"] = None

    return record
```

### Option 4: Skip Problematic Records

For unfixable records, quarantine is the correct behavior:

```bash
# View quarantine statistics
bioetl quarantine-stats --provider chembl --entity activity

# Purge old quarantine (> 30 days)
bioetl quarantine-purge --older-than 30d
```

## Prevention

### Add Schema Tests

```python
# tests/unit/test_chembl_schema.py
def test_activity_schema_handles_null_smiles():
    record = {"activity_id": 1, "canonical_smiles": None}
    result = transform(record)
    assert result["canonical_smiles"] is None
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
- `bioetl_dq_records_processed_total{provider, entity}`
- `bioetl_dq_records_passed_total{provider, entity}`
- `bioetl_dq_records_failed_total{provider, entity}`
- `bioetl_dq_soft_threshold_exceeded_total{provider, entity}`
- `bioetl_dq_check_duration_ms{provider, entity}`

## Escalation

Escalate if:
- Hard threshold exceeded for > 3 consecutive runs
- Error rate increasing over time
- New error type not in known issues
- Upstream API changes suspected
