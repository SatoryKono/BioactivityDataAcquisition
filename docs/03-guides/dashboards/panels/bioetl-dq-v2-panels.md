# BioETL Data Quality v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-dq-v2.json`

## Overview

Dashboard `5. Data Quality` assesses the selected Run ID from saved HTTP evidence. Run ID is always set on this page. Prometheus CURRENT status and TIME RANGE scores are not panels on this dashboard. Shipped dashboard JSON is the source of truth.

The page answer is `SELECTED RUN`. A TIME RANGE value is not shown here and never proves this run.

Validation score metrics that are not on this page stay on the canonical `0.0-1.0` ratio scale.

Selected-run accounting includes input, accepted, Silver/Gold quarantine, contract exclusions, Gold output and the exact Report link. Gold and Silver percentages use the Bronze count as the denominator; a missing denominator stays N/A.

## Key Panels

### Understand Evidence Scope
- **Type:** Text
- **Purpose:** State that this page is the selected Run ID assessment.
- **Data sources:** Operator copy.

### Review Selected Run Status
- **Type:** Table
- **Purpose:** Saved verdict for the exact Run ID. Overall verdict is the data-quality assessment; Processing is the ETL outcome; Trust is the saved Trust verdict and does not authorize replay.
- **Data sources:** `/ops/observability/selected-run-status` with `run_id`.
- **Empty:** `QUERY ERROR` when the request fails. `SELECT RUN` is not a successful empty run.

### Inspect Run Identity
- **Type:** Table
- **Purpose:** Manifest identity for the selected Run ID.
- **Data sources:** `/ops/control-plane/identity-table` with `run_id`.

### Inspect Processed Records
- **Type:** Table
- **Purpose:** Input, accepted, quarantine, exclusions and Gold output for the selected Run ID. Counts are not TIME RANGE scores. Gold/Silver percentages use the Bronze count as the denominator.
- **Data sources:** `/ops/observability/processed-records` with `run_id`.

### Inspect Saved Run Evidence
- **Type:** Row
- **Purpose:** Saved domain and identity detail for the same Run ID.
- **Panels:** `Inspect Selected Run Stages` (saved stage rows for the exact Run ID), `Inspect Selected Run Domains` (domain verdicts of this Run ID; not the page status), `Inspect Selected Run Identity` (full identifiers; the short table is `Inspect Run Identity` on the first screen).
- **Data sources:** `/ops/observability/selected-run-status` with `run_id`.
