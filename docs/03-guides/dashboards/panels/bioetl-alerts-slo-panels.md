# BioETL Alerts & SLO - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-alerts-slo.json`

## Overview

Dashboard `6. Alerts & SLO` monitors active alert state, SLO pressure, alert severity breakdown, and alert details. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Render the shared theme-safe bus `0..6` plus
  `Silver Reject Explorer`, `Explore Logs`, and `Explore Traces`; wraps at
  `1024px` and keeps the current item visibly disabled.
- **Data sources:** Dashboard variables and operator copy.

### 2. Scope
- **Type:** Text
- **Purpose:** Explain dashboard scope and selectors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Active Alert Status
- **Type:** Stat
- **Purpose:** Show current active alert count and severity.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

### 4. Firing Alerts / Range
- **Type:** Stat
- **Purpose:** Show firing alerts in selected range.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

### 5. Critical/Page Alerts
- **Type:** Stat
- **Purpose:** Show critical and page alert count.
- **Data sources:** `ALERTS{alertstate="firing",severity="critical"}` (standard Prometheus metric)

### 6. SLO/SLA Alert Pressure
- **Type:** Stat
- **Purpose:** Show SLO/SLA alert pressure indicators.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

### 7. Firing Alert Details
- **Type:** Table
- **Purpose:** Show detailed information for currently firing alerts with an
  explicit `Global`, `Pipeline`, or `Run` scope badge on every row.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

## Variables

Shared context selectors (aligned with primary dashboards):

- `$workflow` narrows by declarative workflow name.
- `$pipeline` narrows by pipeline name.
- `$run_type` narrows by run type (`incremental`, `backfill`, `rebuild`, …).

Alert panels query the standard Prometheus `ALERTS` metric; severity and alert
name are surfaced in panel queries and the `Firing Alert Details` table, not as
separate template variables in the shipped JSON.

## Notes

- This dashboard focuses on alert state and SLO pressure, not detailed metric breakdowns.
- Global alerts remain visible when dashboard pipeline/workflow selectors are
  set; their `Global` badge prevents false attribution to the selected scope.
- Use with monitoring-index.md for incident-time navigation.
- SLO calculations are based on defined error budgets and burn rates.
