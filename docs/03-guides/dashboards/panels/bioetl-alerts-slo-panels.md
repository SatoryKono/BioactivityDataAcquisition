# BioETL Alerts & SLO - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-alerts-slo.json`

## Обзор

Dashboard `6. Alerts & SLO` is an alert-triage surface. Shipped dashboard JSON
is the source of truth; this mirror lists only the currently declared data
signals so stale metric names do not become governance drift.

## Key Panels

### 1. Active Alert Status
- **Type:** Stat
- **Purpose:** Show whether any alert condition is active for the selected
  operator scope.
- **Data sources:** Grafana alert state; no standalone BioETL Prometheus metric
  family is declared for this panel.

### 2. Firing Alerts / Range
- **Type:** Stat
- **Purpose:** Count firing alerts in the selected range.
- **Data sources:** Grafana alert state.

### 3. Critical/Page Alerts
- **Type:** Stat
- **Purpose:** Highlight page-worthy alert pressure.
- **Data sources:** Grafana alert state.

### 4. SLO/SLA Alert Pressure
- **Type:** Stat
- **Purpose:** Summarize SLO/SLA-related alert pressure.
- **Data sources:** Grafana alert state.

### 5. Firing Alert Details
- **Type:** Table
- **Purpose:** Inspect active alert labels, annotations, and runbook handoffs.
- **Data sources:** Grafana alert state.

## Notes

- The dashboard keeps Prometheus metric-family drift at zero by avoiding legacy
  SLO placeholder names in panel documentation.
- Runtime throughput context is still available elsewhere through
  `bioetl_records_processed_total`; alert-state panels do not redefine that
  metric as an SLO signal.
