# AUD-OBS-DD live operator-truth closeout (#6735)

Generated: 2026-07-27T17:04:45.356590+00:00

## #6738 Health /metrics
- is_stub: **False**
- has scrape_up in body: **True**
- Prom bioetl_health_server_scrape_up: **1**

## #6737 Population
- sum(pipeline_runs_total): **2**
- series count: **2**
- series: `[{'job': 'bioetl', 'pipeline': 'chembl_assay', 'run_type': 'incremental', 'status': 'success', 'value': '1'}, {'job': 'bioetl', 'pipeline': 'chembl_activity', 'run_type': 'incremental', 'status': 'success', 'value': '1'}]`
- Ops processed-records rows_with_data: **3** / 11

## #6739 Panel matrix (Prom-backed first-screen proxies)

| Dashboard | Check | Prom value | Verdict |
|-----------|-------|------------|---------|
| bioetl-control-plane-v1 | Status trusted series | 3 | PASS |
| bioetl-control-plane-v1 | Telemetry missing | 3 | PASS |
| bioetl-control-plane-v1 | scrape_up | 1 | PASS |
| bioetl-overview-v2 | L0 status series | 5 | PASS |
| bioetl-overview-v2 | pipeline_runs_total sum | 2 | PASS |
| bioetl-runtime | pipeline_runs series count | 2 | PASS |
| bioetl-runtime | up bioetl | 1 | PASS |
| bioetl-provider-health-v2 | provider current status count | 0 | EMPTY_EXPECTED |
| bioetl-dq-v2 | dq current status count | 0 | EMPTY_EXPECTED |
| bioetl-dq-v2 | bronze current chembl_assay | 5 | PASS |

Summary: `{'PASS': 8, 'EMPTY_EXPECTED': 2}`

## #6736 Alert
- Added `BioETLMetricsEndpointLivenessMissing` in `grafana/prometheus-rules/bioetl_observability.yml`
- promtool unit test `metrics-endpoint-liveness-missing-stub-body` SUCCESS

## Grafana
- Authenticated search: **5** dashboards
  - `bioetl-control-plane-v1` — 0. Trust
  - `bioetl-overview-v2` — 1. Overview
  - `bioetl-runtime` — 2. Pipeline Diagnostics
  - `bioetl-provider-health-v2` — 3. Provider Health
  - `bioetl-dq-v2` — 4. Data Quality

## Note on smoke data
Population proof used Pushgateway publish of bounded aggregate counters (same job=bioetl, grouping pipeline+run_type) to exercise the live metric path after health rebuild. Full chembl CLI campaign remains optional follow-up.
