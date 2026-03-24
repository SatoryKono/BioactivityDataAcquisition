# Pipeline Failure: High DQ Rate (P2)

*Reference: [RULES.md §3.1.2](../../00-project/RULES.md#312-пороги-ошибок-батча-thresholds)*

> Runtime profile: Local-Only single-instance (ADR-010). Commands and paths assume local execution context.

This runbook describes how to handle pipeline failures due to high Data Quality (DQ) error rates.

## Symptoms
- Pipeline fails with `DataQualityThresholdError` / `DataQualityError`.
- Logs show hard-threshold failure or soft-threshold warning messages from transform/postrun stages.
- Quarantine volume spikes for one pipeline.
- Generated DQ report or metadata sidecar points to the affected run artifacts.

## Thresholds
- **Soft Fail**: > 5% errors (Warning).
- **Hard Fail**: > 20% errors (Pipeline Failure).

## Diagnosis Steps
1. **Inspect Quarantine**:
   ```bash
   bioetl quarantine inspect --pipeline <pipeline-name> --limit 20
   ```
2. **Analyze Error Types**:
   - `SCHEMA-VIOLATION`: Source data doesn't match expected schema.
   - `MISSING-REQUIRED-FIELD`: Mandatory field is null/missing.
   - `INVALID-FORMAT`: Date/Number format is incorrect.

## Recovery Actions
1. **If Source Data is Bad**:
   - Contact data provider.
   - Wait for provider to fix data.
2. **If Schema is Outdated**:
   - Update source-aligned contract/schema code in `src/bioetl/domain/contracts/gold/` or related validation/config modules.
   - Update Pandera-based validation surfaces used by the pipeline.
   - Deploy new version.
3. **If Threshold is Too Strict**:
   - Temporarily increase threshold in `configs/entities/{provider}/{entity}.yaml`:
     ```yaml
     pipeline:
       dq_overrides:
         hard_fail_threshold: 0.30  # Increase to 30%
     ```
   - **Warning**: This degrades data quality in Silver/Gold.

## Quarantine Management
- **Replay**: After fixing the parser/schema, replay quarantined records:
  ```bash
  bioetl quarantine replay --pipeline <pipeline-name>
  ```
- **Purge**: If data is garbage, purge quarantine:
  ```bash
  bioetl quarantine purge --pipeline <pipeline-name> --older-than-days 30
  ```
