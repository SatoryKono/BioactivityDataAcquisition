# BioETL Silver Reject Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-silver-reject-explorer.json`

## Обзор

Silver Reject Explorer is a forensic HTTP-backed dashboard for rejected records.
It does not use Prometheus Silver reject metric families directly. The Data
Quality dashboard owns Prometheus Silver/Gold reject summary metrics and hands
off bounded filters into this explorer.

## Key Panels

### 1. Inspect Explorer Scope
- **Type:** Text
- **Purpose:** Explain the bounded forensic scope and zero-reject semantics.
- **Data sources:** Dashboard variables and operator copy.

### 2. Monitor Explorer Backend Health
- **Type:** Table
- **Purpose:** Distinguish backend failure from an intentionally empty
  zero-reject result set.
- **Data sources:** `/ops/quarantine/health`

### 3. Summary and Trend Panels
- **Type:** Table / Timeseries
- **Purpose:** Show filtered reject totals, reject ratio versus Bronze, and
  selected-range trend.
- **Data sources:** `/ops/quarantine/filtered-stats`,
  `/ops/quarantine/filtered-timeseries`

### 4. Reject Breakdown Panels
- **Type:** Table
- **Purpose:** Inspect top reject reasons, fields, reason signatures, and
  filtered records.
- **Data sources:** `/ops/quarantine/filtered-stats`,
  `/ops/quarantine/records`

### 5. Selected Record Details
- **Type:** Table
- **Purpose:** Inspect a selected payload and copy CLI resolve commands.
- **Data sources:** `/ops/quarantine/records`

## Variables

- `pipeline` is single-select and fail-closed.
- `run_type`, `reason_code`, `field`, `quarantine_run_id`, and `payload_hash`
  are forensic selectors owned by this explorer.

## Notes

- Generic primary-dashboard `run_id` must not be mapped into
  `quarantine_run_id` except through explicit forensic record/payload
  handoffs.
- This dashboard intentionally avoids legacy Prometheus Silver reject rate or
  quarantine placeholder metric names; the DQ dashboard documents the current
  Prometheus summary families.
