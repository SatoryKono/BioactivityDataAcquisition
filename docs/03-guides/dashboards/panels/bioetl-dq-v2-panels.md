# BioETL Data Quality v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-dq-v2.json`

## Overview

Dashboard `5. Data Quality` assesses the selected Run ID from saved HTTP evidence. Run ID is always set on this page. Prometheus CURRENT status and TIME RANGE scores are not panels on this dashboard. Shipped dashboard JSON is the source of truth.

The page answer is `SELECTED RUN`. A TIME RANGE value is not shown here and never proves this run.

Validation score metrics that are not on this page stay on the canonical `0.0-1.0` ratio scale.

Selected-run accounting includes input, accepted, Silver/Gold quarantine, contract exclusions, Gold output and the exact Report link. Excl % uses Silver accepted as the denominator; zero/missing denominator remains unknown.

## Key Panels

### Understand Evidence Scope
- **Type:** Text
- **Purpose:** State that this page is the selected Run ID assessment.
- **Data sources:** Operator copy.

### Review Selected Run Status
- **Type:** Table
- **Purpose:** Saved verdict for the exact Run ID.
- **Data sources:** `/ops/observability/selected-run-status` with `run_id`.
- **Empty:** `QUERY ERROR` when the request fails. `SELECT RUN` is not a successful empty run.

### Inspect Run Identity
- **Type:** Table
- **Purpose:** Manifest identity for the selected Run ID.
- **Data sources:** `/ops/control-plane/identity-table` with `run_id`.

### Inspect Processed Records
- **Type:** Table
- **Purpose:** Input, accepted, quarantine, exclusions and Gold output for the selected Run ID.
- **Data sources:** `/ops/observability/processed-records` with `run_id`.

### Inspect Saved Run Evidence
- **Type:** Row
- **Purpose:** Saved domain and identity detail for the same Run ID.
- **Panels:** `Inspect Selected Run Domains`, `Inspect Selected Run Identity`.
- **Data sources:** `/ops/observability/selected-run-status` with `run_id`.
