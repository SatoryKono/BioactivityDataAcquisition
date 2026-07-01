# BioETL Alerts & SLO - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-alerts-slo.json`

## Overview

Dashboard `6. Alerts & SLO` monitors active alert state, SLO pressure, alert severity breakdown, and alert details. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Scope
- **Type:** Text
- **Purpose:** Explain dashboard scope and selectors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Active Alert Status
- **Type:** Stat
- **Purpose:** Show current active alert count and severity.
- **Data sources:** `bioetl_alerts_active_total`, `bioetl_alerts_active_by_severity`

### 4. Firing Alerts / Range
- **Type:** Stat
- **Purpose:** Show firing alerts in selected range.
- **Data sources:** `bioetl_alerts_firing_total`

### 5. Critical/Page Alerts
- **Type:** Stat
- **Purpose:** Show critical and page alert count.
- **Data sources:** `bioetl_alerts_active_by_severity`

### 6. SLO/SLA Alert Pressure
- **Type:** Stat
- **Purpose:** Show SLO/SLA alert pressure indicators.
- **Data sources:** `bioetl_slo_alert_pressure`, `bioetl_sla_alert_pressure`

### 7. Firing Alert Details
- **Type:** Table
- **Purpose:** Show detailed information for currently firing alerts.
- **Data sources:** `bioetl_alerts_firing_total`, `bioetl_alerts_firing_by_alert_name`

## Variables

- `severity` narrows by alert severity level.
- `provider` narrows by provider.
- `pipeline` narrows by pipeline.
- `alert_name` narrows by specific alert name.

## Notes

- This dashboard focuses on alert state and SLO pressure, not detailed metric breakdowns.
- Use with monitoring-index.md for incident-time navigation.
- SLO calculations are based on defined error budgets and burn rates.
