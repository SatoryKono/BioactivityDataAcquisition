# Pipeline Failure: High DQ Rate (P2)

*Reference: [RULES.md §3.1.2](../../RULES.md#312-пороги-ошибок-батча-thresholds)*

This runbook describes how to handle pipeline failures due to high Data Quality (DQ) error rates.

## Symptoms
- Pipeline fails with `DataQualityError`.
- Logs show "Batch failed DQ check".
- `dq_validation_score` drops below threshold.
- `errors_total{type="data_quality"}` metric spikes.

## Thresholds
- **Soft Fail**: > 5% errors (Warning).
- **Hard Fail**: > 20% errors (Pipeline Failure).

## Diagnosis Steps
1. **Inspect Quarantine**:
   ```bash
   make quarantine-inspect PIPELINE=...
   ```
2. **Analyze Error Types**:
   - `SCHEMA_VIOLATION`: Source data doesn't match expected schema.
   - `MISSING_REQUIRED_FIELD`: Mandatory field is null/missing.
   - `INVALID_FORMAT`: Date/Number format is incorrect.

## Recovery Actions
1. **If Source Data is Bad**:
   - Contact data provider.
   - Wait for provider to fix data.
2. **If Schema is Outdated**:
   - Update Pydantic models in `src/bioetl/domain/entities/`.
   - Update Pandera schemas in `src/bioetl/infrastructure/schemas/`.
   - Deploy new version.
3. **If Threshold is Too Strict**:
   - Temporarily increase threshold in `configs/pipelines/{pipeline}.yaml`:
     ```yaml
     dq_rules:
       hard_fail_threshold: 0.30  # Increase to 30%
     ```
   - **Warning**: This degrades data quality in Silver/Gold.

## Quarantine Management
- **Replay**: After fixing the parser/schema, replay quarantined records:
  ```bash
  make quarantine-replay PIPELINE=...
  ```
- **Purge**: If data is garbage, purge quarantine:
  ```bash
  make quarantine-purge PIPELINE=...
  ```
