______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-03'

______________________________________________________________________

# Pipeline Failure: High DQ Rate (P1)

## Trigger

- Run this procedure for pipeline failures driven by data quality policy violations or invalid datasets.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Symptoms

- Pipeline fails with `DataQualityThresholdError` / `DataQualityError`.
- Logs show hard-threshold failure or soft-threshold warning messages from transform/postrun stages.
- Quarantine volume spikes for one pipeline.
- Generated DQ report or metadata sidecar points to the affected run artifacts.

### Thresholds

- **Soft Fail**: > 5% errors (Warning).
- **Hard Fail**: > 25% errors (Pipeline Failure) for hierarchical configuration; > 20% for contract/runtime fallback.

**Note:** DQ thresholds have dual defaults:
- Hierarchical configuration (`configs/base/quality.yaml`): `soft_fail: 0.05` (5%), `hard_fail: 0.25` (25%)
- Contract/runtime fallback (`src/bioetl/domain/ports/quality/silver_dq_request.py`): `soft_fail_threshold: 0.05` (5%), `hard_fail_threshold: 0.20` (20%)

The hierarchical configuration takes precedence when available.

### Diagnosis Steps

1. **Inspect Quarantine**:
   ```bash
   bioetl quarantine inspect --pipeline <pipeline-name> --limit 20
   ```
1. **Analyze Error Types**:
   - `SCHEMA-VIOLATION`: Source data doesn't match expected schema.
   - `MISSING-REQUIRED-FIELD`: Mandatory field is null/missing.
   - `INVALID-FORMAT`: Date/Number format is incorrect.

### Recovery Actions

1. **If Source Data is Bad**:
   - Contact data provider.
   - Wait for provider to fix data.
1. **If Schema is Outdated**:
   - Update source-aligned contract/schema code in `src/bioetl/domain/contracts/gold/` or related validation/config modules.
   - Update Pandera-based validation surfaces used by the pipeline.
   - Deploy new version.
1. **If Threshold is Too Strict**:
   - Temporarily increase threshold in `configs/entities/{provider}/{entity}.yaml`:
     ```yaml
     pipeline:
       dq_overrides:
         hard_fail_threshold: 0.30  # Increase to 30%
     ```
   - **Warning**: This degrades data quality in Silver/Gold.

### Quarantine Management

- **Replay**: After fixing the parser/schema, replay quarantined records:
  ```bash
  bioetl quarantine replay --pipeline <pipeline-name>
  ```
- **Purge**: If data is garbage, purge quarantine:
  ```bash
  bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
  ```

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
