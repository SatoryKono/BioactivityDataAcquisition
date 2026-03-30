---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Priority: P1
Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
Last verified: '2026-03-30'
---

# Pipeline Failure Recovery Runbook

## Trigger

- Run this procedure when a pipeline must be diagnosed, stabilized, and safely resumed or rebuilt.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Overview

- This runbook covers diagnosing and recovering from failed BioETL pipeline runs.

### Symptoms

- Pipeline exits with non-zero exit code
- Error messages in logs
- Incomplete data in Silver/Gold tables

### Diagnostic Steps

### Step 1: Check Exit Code

```bash
echo $?  # After pipeline run
```

| Exit Code               | Meaning           | Next Step        |
| ----------------------- | ----------------- | ---------------- |
| 1                       | General error     | Check logs       |
| 2                       | Invalid arguments | Review CLI args  |
| 83 (DATA-QUALITY-ERROR) | DQ hard threshold | See DQ runbook   |
| 130                     | SIGINT            | Check checkpoint |
| 143                     | SIGTERM           | Check checkpoint |

### Step 2: Review Logs

```bash
# Find recent log entries with errors
grep -r "error\|ERROR\|exception" logs/ | tail -50

# Check specific run by run-id
grep "run-id.*<run-id>" logs/
```

- Key log fields to examine:

- `error-category`: CRITICAL, RECOVERABLE, or DATA-QUALITY
- `status-code`: HTTP status if external API error
- `retry-count`: Number of retry attempts
- `provider`: Which data source failed

### Step 3: Check Checkpoint State

```bash
cat data/output/checkpoints/{pipeline}.json
```

- Checkpoint contains:

- `pipeline`: Pipeline name
- `run_id`: Run identifier of the checkpoint owner
- `metadata.records_processed`: Offset-like progress counter used for resume
- `version`: Checkpoint payload version

### Step 4: Identify Error Type

- **Critical Errors (Fail Immediately)**

- Authentication failures (401, 403)
- Schema mismatch in Gold layer
- Database unavailable

- **Recoverable Errors (Auto-Retry)**

- Rate limits (429)
- Timeouts (502, 503, 504)
- Temporary network issues

- **Data Quality Errors (Skip Record)**

- Invalid SMILES strings
- Missing required fields
- Value out of range

### Recovery Procedures

### Resume from Checkpoint

- For recoverable failures, simply resume:

```bash
bioetl run --pipeline chembl_activity --resume
```

- The pipeline will:

1. Load checkpoint state
1. Resume from `metadata.records_processed`
1. Continue processing

- **Important:** pipelines configured with `loading_strategy: full_scan_only` do not resume from checkpoint even when `--resume` is requested.

### Force Full Refresh

- If checkpoint is corrupted or data inconsistent:

```bash
# Clear checkpoint and reprocess all data
bioetl run --pipeline chembl_activity --run-type rebuild
```

- **Warning**: This will reprocess all records from the beginning.

### Clear and Rebuild Silver

- For schema issues or data corruption:

```bash
# 1. Backup current Silver table
mv data/output/silver/chembl/activity data/output/silver/chembl/activity.bak

# 2. Clear checkpoint only after the failed process has stopped
rm data/output/checkpoints/chembl_activity.json

# 3. Full refresh
bioetl run --pipeline chembl_activity --run-type rebuild

# 4. Verify data
Для проверки данных используйте: `bioetl run --pipeline chembl_activity --run-type rebuild --limit 10`

# 5. Remove backup if successful
rm -rf data/output/silver/chembl/activity.bak
```

### Handle Authentication Errors

- For 401/403 errors:

1. Check API key validity
1. Verify environment variables:
   ```bash
   echo $BIOETL_CHEMBL_API_KEY
   echo $BIOETL_UNIPROT_API_KEY
   ```
1. Rotate API key if expired
1. Resume pipeline

### Handle Rate Limit Errors

- For persistent 429 errors:

1. Check current rate limit configuration in pipeline YAML
1. Reduce batch size if needed:
   ```yaml
   # configs/entities/chembl/activity.yaml
   batch-size: 500  # Reduce from default
   ```
1. Add delay between requests:
   ```yaml
   rate-limit:
     requests-per-second: 5  # Reduce if hitting limits
   ```
1. Resume pipeline

### Prevention

### Enable Monitoring

- Set up alerts for:

- Pipeline failures (exit code != 0)
- DQ threshold warnings (soft threshold exceeded)
- Long-running pipelines (> expected duration)

### Regular Maintenance

- Run VACUUM weekly (see [VACUUM Procedures](vacuum-procedures.md))
- Monitor checkpoint file sizes
- Review the unified quarantine table for patterns (`bioetl quarantine stats --pipeline ...`)

### Escalation

- If recovery fails after 3 attempts:

1. Document error details
1. Check for upstream API issues
1. Review recent code changes
1. Escalate to development team

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
