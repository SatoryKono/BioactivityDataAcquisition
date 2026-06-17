# BioETL Data Quality v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-dq-v2.json`

## Обзор

Dashboard `4. Data Quality` monitors DQ current status, validation score,
freshness, quarantine, Silver structural rejects, and Gold contract-semantic
reject outcomes. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Monitor DQ Current Status
- **Type:** Stat / Table
- **Purpose:** Show current DQ severity and reason details.
- **Data sources:** `bioetl_dq_current_status`, `bioetl_dq_current_reason`

### 2. Data Quality Score
- **Type:** Gauge / Timeseries
- **Purpose:** Volume-weighted DQ score and trend.
- **Data sources:** `bioetl_dq_validation_score`,
  `bioetl_dq_validation_record_count`

### 3. Bronze -> Silver -> Gold Range Evidence
- **Type:** Timeseries / Stat
- **Purpose:** Compare selected-range record flow and invariant status.
- **Data sources:** `bioetl_records_processed_total`,
  `bioetl_record_flow_invariants_total`

### 4. Silver Structural Rejects
- **Type:** Stat / Bargauge
- **Purpose:** Track records filtered out before Gold semantics and inspect
  reject reason/field breakdowns.
- **Data sources:** `bioetl_records_processed_total`,
  `bioetl_silver_filter_rejections_total`,
  `bioetl_silver_filter_reject_total_mismatch_15m`

### 5. Gold Contract-Semantic Reject Outcomes
- **Type:** Bargauge / Stat
- **Purpose:** Keep Gold contract outcomes separate from Silver structural
  rejects.
- **Data sources:** `bioetl_processed_records_gold_quarantined_current`,
  `bioetl_processed_records_gold_excluded_by_contract_current`,
  `bioetl_dq_validation_failures_total`

### 6. Quarantine and Freshness
- **Type:** Stat / Gauge / Bargauge
- **Purpose:** Surface quarantined records, freshness lag, anomalies, and DQ
  threshold events.
- **Data sources:** `bioetl_dq_records_quarantined_total`,
  `bioetl_data_freshness_seconds`, `bioetl_dq_anomaly_detected`,
  `bioetl_dq_soft_threshold_exceeded`, `bioetl_silver_validation_failures_total`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary
  dashboard context shell.
- `stage` narrows medallion-stage range evidence where the panel owns that
  selector.

## Notes

- Silver and Gold reject observability are intentionally distinct:
  `bioetl_silver_filter_rejections_total` and filtered-out stage accounting
  represent Silver structural rejects, while Gold uses Gold outcome recording
  rules and validation failure metrics.
- Legacy aggregate names for generic DQ scores, rule pass rates, Silver reject
  rates, and validation errors are intentionally not documented here.
