# BioETL Silver Reject Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-silver-reject-explorer.json`

## Overview

Dashboard `Silver Reject Explorer` provides detailed Silver structural reject evidence with reject reason/field breakdowns and pipeline-specific filtering. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Review Dashboard Navigation
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Inspect Explorer Scope
- **Type:** Text
- **Purpose:** Explain explorer scope and selectors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Monitor Explorer Backend Health
- **Type:** Table
- **Purpose:** Show explorer backend health status.
- **Data sources:** HTTP quarantine backend health checks.

### 4. Review: First Action / No-Data Semantics
- **Type:** Text
- **Purpose:** Guide operator to next triage action or explain no-data semantics.
- **Data sources:** Dashboard variables and operator copy.

### 5. Monitor Filtered Records Total
- **Type:** Table
- **Purpose:** Show total filtered records by pipeline.
- **Data sources:** `bioetl_silver_filter_rejections_total`

### 6. Track Reject Rate vs Bronze
- **Type:** Table
- **Purpose:** Show reject rate compared to Bronze records.
- **Data sources:** `bioetl_silver_filter_rejections_total`, `bioetl_records_processed_total`

### 7. Inspect Run Scope Summary
- **Type:** Table
- **Purpose:** Show run scope summary for selected filters.
- **Data sources:** `bioetl_silver_filter_rejections_total`

### 8. Track Filtered Rejects Over Time
- **Type:** Timeseries
- **Purpose:** Show Silver reject trend over time.
- **Data sources:** `bioetl_silver_filter_rejections_total`

### 9. Track Reject Ratio vs Bronze Over Time
- **Type:** Timeseries
- **Purpose:** Show reject ratio compared to Bronze over time.
- **Data sources:** `bioetl_silver_filter_rejections_total`, `bioetl_records_processed_total`

### 10. Inspect Top Reject Reasons
- **Type:** Table
- **Purpose:** Show top reject reasons.
- **Data sources:** `bioetl_silver_filter_reject_reason_total`

### 11. Inspect Top Reject Fields
- **Type:** Table
- **Purpose:** Show top reject fields.
- **Data sources:** `bioetl_silver_filter_reject_field_total`

### 12. Inspect Top Reason Signatures
- **Type:** Table
- **Purpose:** Show top reason signatures.
- **Data sources:** `bioetl_silver_filter_reject_reason_total`

### 13. Review: Trend Empty State
- **Type:** Text
- **Purpose:** Keep trend empty-state semantics visible when active filters
  return no matching reject samples.
- **Data sources:** Dashboard variables and operator copy.

### 14. Review: Record Selection Empty State
- **Type:** Text
- **Purpose:** Keep record-selection guidance visible even when empty HTTP table
  frames do not render field-level `noValue` text.
- **Data sources:** Dashboard variables and operator copy.

### 15. Inspect Filtered Records Table
- **Type:** Table
- **Purpose:** Show a compact latest-record list and an explanatory empty state
  when filters return no rows.
- **Data sources:** HTTP quarantine backend filtered records query.

### 16. Inspect Selected Record Details
- **Type:** Table
- **Purpose:** Show compact one-record details after `payload_hash` selection,
  or guide the operator to select a row, widen filters, or verify backend
  health when no record is selected.
- **Data sources:** HTTP quarantine backend record detail query.

## Variables

- `pipeline` is the primary selector for pipeline-specific evidence.
- `reason_code` narrows by specific reject reason.
- `field` narrows by specific field name.
- `quarantine_run_id` narrows by specific reject run without becoming a shared
  shell `run_id` selector.
- `payload_hash` focuses the selected record details panel.

## Notes

- This dashboard focuses on Silver structural rejects, not Gold contract-semantic rejects.
- Use with `bioetl quarantine inspect --pipeline <pipeline>` for detailed record-level evidence.
- Reject reasons are derived from Silver validation rules and filter logic.
- Explorer backend health is monitored via HTTP quarantine backend health checks.
