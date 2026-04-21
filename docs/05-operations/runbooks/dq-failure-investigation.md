______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-03-30'

______________________________________________________________________

# DQ Failure Investigation Runbook

## Trigger

- Run this procedure when data quality alerts, validation failures, or quarantine outcomes require investigation.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Overview

- Data Quality (DQ) checks ensure data integrity throughout the pipeline. This runbook covers investigating DQ threshold violations and data quality issues.

### DQ Thresholds

| Threshold | Default | Behavior                                              |
| --------- | ------- | ----------------------------------------------------- |
| Soft      | 5%      | Warning logged, pipeline continues                    |
| Hard      | 20%     | Pipeline fails with exit code 83 (DATA-QUALITY-ERROR) |

- Configuration:

```yaml
# configs/entities/chembl/activity.yaml
quality:
  thresholds:
    soft_fail: 0.05  # 5%
    hard_fail: 0.20  # 20%
```

### Symptoms

- Pipeline exits with code 83 (DATA-QUALITY-ERROR, DQ hard threshold)
- Log messages: `DQ Soft Threshold exceeded`
- Prometheus metric: `bioetl_dq_soft_threshold_exceeded`
- Records in quarantine directory

### Investigation Steps

### Step 1: Identify Failure Scope

- Check logs for DQ summary:

```bash
grep "dq-check\|dq-threshold" reports/logs/bioetl.log | tail -20
```

- Key log fields:

- `error_rate`: Percentage of quarantined records in the evaluated batch

- `quarantined_count`: Absolute count

- `total_count`: Total records in batch

- `pipeline`: Pipeline name tied to the warning/failure

### Step 2: Examine Quarantine Records

- Quarantined records are stored in unified Delta table:

```
data/output/quarantine
```

```bash
# Inspect recent records for one pipeline
bioetl quarantine inspect --pipeline chembl_activity --limit 10
```

- Quarantine record structure:

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

- Common DQ error categories:

| Category        | Examples                 | Severity |
| --------------- | ------------------------ | -------- |
| Missing fields  | `null` in required field | Medium   |
| Invalid format  | Bad SMILES, invalid date | High     |
| Out of range    | Negative IC50, >1M MW    | Medium   |
| Type mismatch   | String in numeric field  | High     |
| Encoding issues | Invalid UTF-8            | Low      |

```bash
# CLI dashboard
# (includes by_error_code/by_status and oldest/newest timestamps)
bioetl quarantine stats --pipeline chembl_activity
```

### Step 4: Root Cause Analysis

- **Source Data Issues**

- Check if upstream API changed response format

- Verify API version in use

- Compare with known-good historical data

- **Schema Evolution**

- Check if new fields were added upstream

- Verify transformer handles optional fields

- Review schema validation rules

- **Pipeline Bug**

- Review recent code changes to transformer

- Check for off-by-one errors in parsing

- Verify type coercion logic

### Step 5: Impact Assessment

```python
from deltalake import DeltaTable
import polars as pl

# Check current Silver table state
dt = DeltaTable("data/output/silver/chembl/activity")
df = pl.scan - delta(str(dt)).collect()

# Count records by run_id
run_stats = df.group_by("_run_id").agg(
    [
        pl.len().alias("records"),
        pl.col("_dq_passed").sum().alias("passed"),
    ]
)
print(run_stats)
```

### Resolution Procedures

### Option 1: Fix and Reprocess Quarantine

- For fixable issues (e.g., encoding, format):

```python
import json
from pathlib import Path


def reprocess_quarantine(quarantine_dir: str, output_file: str) -> None:
    """Extract and fix quarantined records."""
    fixed_records = []

    for f in Path(quarantine_dir).glob("*.jsonl"):
        for line in f.read - text().splitlines():
            record = json.loads(line)
            original = record.get("payload", {})

            # Apply fixes based on error type
            if record.get("error_code") == "ENCODING_ERROR":
                # Fix encoding
                field_value = original.get("field")
                if isinstance(field_value, str):
                    original["field"] = field_value.encode("utf-8", "ignore").decode()
                fixed_records.append(original)

    with open(output_file, "w", encoding="utf-8") as f:
        for record in fixed_records:
            f.write(json.dumps(record) + "\n")

    print(f"Fixed {len(fixed_records)} records")
```

### Option 2: Adjust Thresholds

- If DQ issues are expected (e.g., known data quality in source):

```yaml
# Temporarily relax thresholds
pipeline:
  dq_overrides:
    soft_fail_threshold: 0.10  # 10%
    hard_fail_threshold: 0.30  # 30%
```

- **Warning**: Document why thresholds were changed!

### Option 3: Add Data Cleansing

- For systematic issues, add cleansing to transformer:

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

- For unfixable records, quarantine is the correct behavior:

```bash
# View quarantine statistics
bioetl quarantine stats --pipeline chembl_activity

# Purge old quarantine (> 30 days)
bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
```

### Prevention

### Add Schema Tests

```python
# tests/unit/test-chembl-schema.py
def test-activity-schema-handles-null-smiles():
    record = {"activity-id": 1, "canonical-smiles": None}
    result = transform(record)
    assert result["canonical-smiles"] is None
```

### Monitor DQ Trends

- Set up dashboards for:

- DQ error rate over time

- Error type distribution

- Records quarantined per run

- Alert on:

- Soft threshold exceeded

- New error type appearing

- Sudden spike in quarantine rate

### Document Known Issues

- Maintain a list of known DQ issues:

```markdown
# Known DQ Issues

| Provider | Entity | Issue | Workaround | Status |
|----------|--------|-------|------------|--------|
| ChEMBL | activity | Empty SMILES | Treat as null | Accepted |
| PubChem | compound | Invalid InChI | Skip record | Investigating |
```

### Metrics

- Key Prometheus metrics:

- `bioetl_records_processed_total{pipeline, stage, run_type}`

- `bioetl_dq_validation_score{pipeline, entity}`

- `bioetl_dq_validation_record_count{pipeline, entity}`

- `bioetl_dq_validation_failures_total{pipeline, stage, severity}`

- `bioetl_dq_records_quarantined_total{pipeline, entity, error_type}`

- `bioetl_dq_soft_threshold_exceeded{pipeline}`

- `bioetl_dq_check_duration_ms{pipeline}`

### Provenance Notes

- Silver metadata may include `dq_summary.rule_provenance` when the pipeline passes `dq_rule_provenance` into metadata assembly.
- Gold metadata carries `dq_report_path` and schema contract metadata, but does not yet have a separate Gold-only `dq_rule_provenance` field.
- Current DQ runtime is threshold-driven first; a fully contract-bound `contract_version -> rule_id -> disposition` chain is not yet a repo-wide invariant.

### Escalation

- Escalate if:

- Hard threshold exceeded for > 3 consecutive runs

- Error rate increasing over time

- New error type not in known issues

- Upstream API changes suspected

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
