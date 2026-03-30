# Grafana Dashboard Audit

Date: 2026-03-30

## Scope

Current shipped dashboards from [grafana/dashboards](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards):

- `bioetl-overview-v2`
- `bioetl-dq-v2`
- `bioetl-provider-health-v2`
- `bioetl-runtime`

Audit evidence sources:

- shipped dashboard JSON files in [grafana/dashboards](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards)
- latest Playwright review snapshot [grafana-dashboard-review.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/reports/review/playwright/grafana-dashboard-review.json)
- screenshots in [output/playwright](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright)

## Limitations

- Live Grafana was unavailable during this audit:
  - `http://localhost:3000` -> connection refused
  - `http://localhost:9090` -> connection refused
- Because live backends were down, this is an offline audit based on dashboard definitions plus the latest available screenshot/review snapshot.
- `bioetl-runtime` has no current screenshot/review artifact in the repository, so its panel fill state could not be verified visually.
- `bioetl-simple` appears in the Playwright review snapshot but is not present in the current shipped dashboard directory, so it is excluded from the main audit scope.

## Dashboard Reports

### 1. Overview

Dashboard file: [bioetl-overview-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-overview-v2.json)  
Snapshot: [bioetl-overview-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-overview-v2.png)

Overall status: Partial / degraded  
Confidence: Medium

Visible snapshot findings:

- `Pipeline` [text]: populated
- `Execution Timestamp` [stat]: populated, shows `03/28/2026, 03:53:26 PM`
- `Processing Pipeline` [timeseries]: populated
- `Stage Distribution` [piechart]: populated
- `Pipeline Distribution` [piechart]: populated
- `Overall Quality` [gauge]: populated, `100.0%`
- `Control Plane & Lineage` [text]: populated
- `Manifest Write Failures` [stat]: `No data`
- `Ledger Append Failures` [stat]: `No data`
- `Checkpoint Incompatibilities` [stat]: `No data`
- `Lineage Refs Missing` [stat]: `No data`
- `Lineage Fragment Outcomes` [timeseries]: populated

Panels defined in JSON but not directly visible in the captured screenshot:

- `Control-plane Lookup Failures` [stat]: query present, live fill not verified
- `Control-plane Lookup p95` [stat]: query present, live fill not verified
- `Silver Filter Rejects` [stat]: query present, live fill not verified
- `Silver Filter Reject Rate` [gauge]: query present, live fill not verified

Detected problems:

- Four control-plane stat panels display `No data`.
- These panels use PromQL with `or vector(0)` fallback, so an operator would normally expect a rendered zero instead of `No data`.
- Snapshot timestamp is from 2026-03-28, so the reviewed data is stale relative to the audit date.

Possible causes:

- corresponding control-plane metrics are not being emitted
- Prometheus scrape gap or datasource problem at capture time
- label mismatch for `pipeline` / `run_type`
- panel reduction / stat configuration causing empty result rendering despite fallback

Recommendations:

- validate the four control-plane panel queries directly in Grafana Explore once Grafana is back up
- verify that `bioetl_control_plane_*`, `bioetl_checkpoint_*`, and `bioetl_lineage_*` metrics are present in Prometheus
- confirm whether the stat panels should render `0` instead of `No data`
- capture a fresh full-page screenshot including panels 116-119

### 2. Data Quality

Dashboard file: [bioetl-dq-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-dq-v2.json)  
Snapshot: [bioetl-dq-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-dq-v2.png)

Overall status: Partial / degraded  
Confidence: Medium

Visible snapshot findings:

- `Pipeline` [text]: populated
- `Execution Timestamp` [stat]: populated, shows `03/28/2026, 03:53:26 PM`
- `Data Flow: Bronze -> Silver -> Gold` [timeseries]: populated
- `Data Quality Score` [gauge]: populated, `100.0%`
- `Source Records (Bronze)` [stat]: populated, `10`
- `Clean Records (Gold)` [stat]: populated, `10`
- `DQ Validation Score` [gauge]: populated, `100.0%`
- `Records Quarantined` [stat]: `No data`
- `Soft Threshold Exceeded` [stat]: `No data`
- `Data Freshness Lag (seconds)` [gauge]: populated, `55 mins`
- `Quarantine by Error Type` [piechart]: `No data`
- `Anomalies Detected` [timeseries]: `No data`
- `DQ Check Duration (p95)` [timeseries]: `No data`
- `Silver Validation Failures` [stat]: `No data`
- `Lineage Refs Missing` [stat]: `No data`

Panels defined in JSON but not directly visible in the captured screenshot:

- `Silver Filter Rejects` [stat]: query present, live fill not verified
- `Silver Filter Rejects by Pipeline` [bargauge]: query present, live fill not verified

Detected problems:

- Seven panels show `No data` in the review snapshot.
- Four stat panels are especially suspicious:
  - `Records Quarantined`
  - `Soft Threshold Exceeded`
  - `Silver Validation Failures`
  - `Lineage Refs Missing`
- Those four panels also use fallback patterns that would usually be expected to render `0`, not `No data`.

Potentially acceptable empty states, but still needing confirmation:

- `Quarantine by Error Type`
- `Anomalies Detected`
- `DQ Check Duration (p95)`

Possible causes:

- metrics absent for quarantine / validation / lineage signals
- Prometheus label mismatch for `pipeline` or `run_type`
- DQ checks not emitting duration/anomaly series for the selected scope
- stat/pie/timeseries panels configured to show empty state when series are absent

Recommendations:

- validate all seven empty panels in Grafana Explore with the selected `$pipeline` and `$run_type`
- verify that DQ and lineage metrics exist in Prometheus for `chembl_activity`
- make zero-state stat panels render explicit `0` where appropriate
- capture a fresh screenshot that also includes panels 117-118

### 3. Provider Health

Dashboard file: [bioetl-provider-health-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-provider-health-v2.json)  
Snapshot: [bioetl-provider-health-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-provider-health-v2.png)

Overall status: Problematic  
Confidence: Medium

Visible snapshot findings:

- `Health Check Latency by Provider (p95)` [timeseries]: populated
- `Health Check Successes (15m)` / `Healthy Checks` [stat]: `No data` in the current snapshot
- `Provider Failure Rate` [gauge]: `No data`
- `Health Checks Total` [stat]: populated, value `0`
- `Provider Health Check Latency (p95) - $provider` [gauge]: populated, value `9.500 ms`
- `Selected Providers` [row]: present / collapsed

Panel defined in JSON but not directly visible as a standalone stat in the captured screenshot:

- `Degraded Checks` [stat]: query present, live fill not verified

Detected problems:

- Two panels are confirmed `No data`:
  - `Healthy Checks`
  - `Provider Failure Rate`
- Cross-panel inconsistency is visible:
  - latency panels have data
  - selected-provider latency gauge has data
  - `Health Checks Total` is `0`
  - `Healthy Checks` is `No data`

Possible causes:

- histogram latency metric is present but success/degraded/failure counters are missing
- provider label mismatch between histogram and counter metrics
- gauge/stat queries and time range are not aligned
- scrape/source inconsistency at snapshot time

Recommendations:

- compare `bioetl_health_check_latency_seconds_*` vs `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`, and `bioetl_health_check_failures_total` in Prometheus
- verify provider label values and variable interpolation for `$provider`
- normalize empty-state behavior so health counters show `0` rather than `No data` when appropriate
- capture a refreshed screenshot with the row expanded

### 4. Runtime

Dashboard file: [bioetl-runtime.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-runtime.json)

Overall status: Not fully verifiable  
Confidence: Low

Offline configuration audit:

- Dashboard contains 17 panels.
- All non-text panels have query targets.
- Datasource mix appears intentional:
  - Loki-backed runtime/log panels
  - Prometheus-backed alert and control-plane panels
- `Log Hygiene Trend` uses two targets.

Panel inventory from JSON:

- `Runtime Scope` [text]: config present
- `Warnings` [stat]: config present
- `Unstructured Logs` [stat]: config present
- `Pipeline Alert Conditions` [stat]: config present
- `DQ Alert Conditions` [stat]: config present
- `Control-plane Alert Conditions` [stat]: config present
- `Provider Alert Conditions` [stat]: config present
- `Freshness Alert Conditions` [stat]: config present
- `DQ Context Failures` [stat]: config present
- `DQ Reports Skipped` [stat]: config present
- `DQ Reports Generated` [stat]: config present
- `Control-plane Lookup Outcomes` [timeseries]: config present
- `Control-plane Lookup p95` [stat]: config present
- `Top Warning Events` [bargauge]: config present
- `Trace-enabled Runs` [stat]: config present
- `Silver Filter Rejects` [stat]: config present
- `Log Hygiene Trend` [timeseries]: config present

Detected problems:

- No live validation was possible because Grafana and Prometheus were unavailable.
- No current screenshot/review artifact for this dashboard exists in the repository.
- Therefore fill status for every runtime panel remains unverified.

Possible causes:

- audit limitation only; not enough runtime evidence

Recommendations:

- capture a live Playwright review for `bioetl-runtime`
- verify Loki datasource connectivity before the next audit
- validate top warning, unstructured logs, and alert-condition panels against a known recent run window

## Summary Table

| Dashboard | Status | Panels | Confirmed issues | Criticality | Brief conclusion |
|---|---|---:|---:|---|---|
| `bioetl-overview-v2` | Partial / degraded | 16 | 4 | Medium | Core throughput panels work, but control-plane visibility is degraded by `No data` stats. |
| `bioetl-dq-v2` | Partial / degraded | 17 | 4 confirmed, 3 need confirmation | Medium-High | Core quality KPIs render, but several DQ / lineage panels are empty and need validation. |
| `bioetl-provider-health-v2` | Problematic | 7 | 3 | High | Health counters are inconsistent with latency data, so provider-health picture is unreliable. |
| `bioetl-runtime` | Not fully verifiable | 17 | not verified | Medium | Dashboard config is present, but runtime fill state could not be validated without live Grafana/Loki/Prometheus. |

## Final Conclusion

- The repository contains four current shipped Grafana dashboards.
- At least three dashboards have evidence of incomplete or unreliable data filling in the latest available review snapshot.
- The most concerning dashboard is `bioetl-provider-health-v2`, because it shows conflicting health signals across panels.
- `bioetl-runtime` cannot be signed off until a fresh live review is captured.
- A follow-up audit should be run after restoring local Grafana/Prometheus availability.
