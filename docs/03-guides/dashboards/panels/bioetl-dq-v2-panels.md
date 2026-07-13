# BioETL Data Quality v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-dq-v2.json`

## Overview

Dashboard `4. Data Quality` monitors DQ current status, validation score, freshness, quarantine, Silver structural rejects, and Gold contract-semantic reject outcomes. Shipped dashboard JSON is the source of truth.

Visible scope vocabulary is strict: headline cards are `CURRENT`, HTTP identity
is `SELECTED RUN`, and score/count/freshness evidence below the answer row is
`TIME RANGE`. A TIME RANGE value never proves an exact run result.

## Key Panels

### 1. Review Dashboard Navigation
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Provenance
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Status
- **Type:** Stat
- **Purpose:** Current DQ severity for the selected scope.
- **Data sources:** `bioetl_dq_current_status`

### 4. ID
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp.
- **Data sources:** `bioetl_pipeline_runs`

### 5. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage.
- **Data sources:** `bioetl_records_processed_total`

### 6. Track Range Evidence: Bronze -> Silver -> Gold
- **Type:** Timeseries
- **Purpose:** Compare selected-range record flow and invariant status.
- **Data sources:** `bioetl_records_processed_total`, `bioetl_record_flow_invariants_total`

### 7. Monitor DQ Current Status
- **Type:** Stat
- **Purpose:** Show current DQ status.
- **Data sources:** `bioetl_dq_current_status`

### 8. Monitor DQ Threshold State
- **Type:** Stat
- **Purpose:** Show DQ threshold state.
- **Data sources:** `bioetl_dq_soft_threshold_exceeded`

### 9. Inspect DQ Current Reasons
- **Type:** Table
- **Purpose:** Show DQ failure reasons.
- **Data sources:** `bioetl_dq_current_reason`

### 10. Review: First Action
- **Type:** Text
- **Purpose:** Guide operator to next triage action.
- **Data sources:** Dashboard variables and operator copy.

### 11. Monitor: Data Quality Score (Volume-weighted)
- **Type:** Stat
- **Purpose:** Show TIME RANGE volume-weighted DQ score as neutral supporting evidence.
- **Data sources:** `bioetl_dq_validation_score`

### 12. Track: Source Records in Range (Bronze)
- **Type:** Stat
- **Purpose:** Count Bronze records in range.
- **Data sources:** `bioetl_records_processed_total`

### 13. Track: Clean Records in Range (Gold)
- **Type:** Stat
- **Purpose:** Count Gold records in range.
- **Data sources:** `bioetl_records_processed_total`

### 14. Monitor: Worst-Entity DQ Score
- **Type:** Stat
- **Purpose:** Show TIME RANGE worst-entity DQ score as neutral supporting evidence.
- **Data sources:** `bioetl_dq_validation_score`

### 15. Track: Records Quarantined in Range
- **Type:** Stat
- **Purpose:** Count quarantined records.
- **Data sources:** `bioetl_dq_records_quarantined_total`

### 16. Track: Silver Validation Failures in Range
- **Type:** Stat
- **Purpose:** Count Silver validation failures.
- **Data sources:** `bioetl_silver_validation_failures_total`

### 17. Time Range · Worst Freshness Age (hours; SLA 24/72)
- **Type:** Gauge
- **Purpose:** Show worst TIME RANGE freshness age in hours. WARN begins at
  `24h`, CRIT at `72h`; query output, unit, title, and thresholds use hours.
- **Data sources:** `bioetl_data_freshness_seconds`

### 18. Track: DQ Blocked Records in Range (Evidence)
- **Type:** Stat
- **Purpose:** Count DQ blocked records.
- **Data sources:** `bioetl_dq_blocked_records`

### 19. Review: Latest Successful Data Timestamp
- **Type:** Stat
- **Purpose:** Show latest successful data timestamp.
- **Data sources:** `bioetl_data_freshness_seconds`

### 20. Track: Silver Filter Rejects in Range
- **Type:** Stat
- **Purpose:** Count Silver filter rejects.
- **Data sources:** `bioetl_silver_filter_rejections_total`

### 21. Silver Structural / Gold Contract-Semantic Rejects
- **Type:** Row
- **Purpose:** Collapsed-by-default reject analysis; expand after current reasons
  or TIME RANGE delivery-impact cards identify a reject path.
- **Data sources:** `bioetl_silver_filter_rejections_total`, `bioetl_dq_validation_failures_total`

### 22. Monitor: Silver Filter Reject Accounting Mismatch
- **Type:** Stat
- **Purpose:** Detect Silver filter reject accounting mismatch.
- **Data sources:** `bioetl_silver_filter_reject_total_mismatch_15m`

### 23. Inspect: Silver Filter Rejects by Pipeline
- **Type:** Bargauge
- **Purpose:** Show Silver rejects by pipeline.
- **Data sources:** `bioetl_silver_filter_rejections_total`

### 24. Inspect: Gold Reject Outcomes by Pipeline
- **Type:** Bargauge
- **Purpose:** Show Gold reject outcomes by pipeline.
- **Data sources:** `bioetl_processed_records_gold_quarantined_current`, `bioetl_processed_records_gold_excluded_by_contract_current`

### 25. Inspect: Top Silver Reject Reasons (Pareto)
- **Type:** Bargauge
- **Purpose:** Show top Silver reject reasons.
- **Data sources:** `bioetl_silver_filter_reject_reason_total`

### 26. Inspect: Top Silver Reject Fields
- **Type:** Bargauge
- **Purpose:** Show top Silver reject fields.
- **Data sources:** `bioetl_silver_filter_reject_field_total`

### 27. Validation Failures / Runtime Diagnostics / Trends
- **Type:** Row
- **Purpose:** Collapsed-by-default validation/runtime/trend forensics.
- **Data sources:** `bioetl_dq_validation_failures_total`, `bioetl_dq_anomaly_detected`

### 28. Inspect: Quarantine by Error Type
- **Type:** Bargauge
- **Purpose:** Show quarantine by error type.
- **Data sources:** `bioetl_dq_records_quarantined_total`

### 29. Track: Anomalies Detected
- **Type:** Timeseries
- **Purpose:** Show anomaly detection trend.
- **Data sources:** `bioetl_dq_anomaly_detected`

### 30. Track: DQ Check Duration (p95)
- **Type:** Timeseries
- **Purpose:** Show DQ check duration p95.
- **Data sources:** `bioetl_dq_check_duration_seconds`

### 31. Monitor: Silver Validation Failures
- **Type:** Stat
- **Purpose:** Count Silver validation failures.
- **Data sources:** `bioetl_silver_validation_failures_total`

### 32. Review: Lineage Handoff to Control Plane
- **Type:** Text
- **Purpose:** Explain lineage handoff to control plane.
- **Data sources:** Dashboard variables and operator copy.

### 33. Track: Data Quality Score Trend (Volume-weighted)
- **Type:** Timeseries
- **Purpose:** Show DQ score trend over time.
- **Data sources:** `bioetl_dq_validation_score`

### 34. Track: DQ Threshold Events in Range Trend
- **Type:** Timeseries
- **Purpose:** Show DQ threshold events trend.
- **Data sources:** `bioetl_dq_soft_threshold_exceeded`

### 35. Review: Aggregate Control-plane Handoff
- **Type:** Text
- **Purpose:** Explain aggregate control-plane handoff.
- **Data sources:** Dashboard variables and operator copy.

### 36. Monitor: Gold Strict Validation Failures
- **Type:** Stat
- **Purpose:** Count Gold strict validation failures.
- **Data sources:** `bioetl_dq_validation_failures_total`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows medallion-stage range evidence where the panel owns that selector.

## Notes

- Silver and Gold reject observability are intentionally distinct:
  `bioetl_silver_filter_rejections_total` and filtered-out stage accounting
  represent Silver structural rejects, while Gold uses Gold outcome recording
  rules and validation failure metrics.
- Legacy aggregate names for generic DQ scores, rule pass rates, Silver reject
  rates, and validation errors are intentionally not documented here.
- `Track: Records Quarantined in Range`, `Track: Silver Filter Rejects in
  Range`, and `Track: DQ Blocked Records in Range (Evidence)` render a zero as
  neutral valid-empty TIME RANGE evidence. They do not override a CURRENT
  WARN/CRIT verdict.
