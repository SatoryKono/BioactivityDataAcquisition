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
- fresh live screenshots in [output/playwright](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright)
- direct live checks against local Grafana / Prometheus / Loki during the audit

## Audit Method

- dashboards were reviewed from the shipped JSON definitions
- screenshots were re-rendered from live Grafana via Playwright
- empty-state panels were checked against their current query semantics
- placeholder / zero-state rendering was treated as valid only where the absence of events is expected behavior

## Dashboard Reports

### 1. Overview

Dashboard file: [bioetl-overview-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-overview-v2.json)
Screenshot: [bioetl-overview-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-overview-v2.png)

Overall status: Healthy dashboard with live pipeline degradation signal
Confidence: High

Verified panels:

- `Pipeline` [text]: populated, `chembl_activity`
- `Execution Timestamp` [stat]: populated, `03/30/2026, 10:44:50 AM`
- `Processing Pipeline` [timeseries]: populated
- `Stage Distribution` [piechart]: populated
- `Pipeline Distribution` [piechart]: populated
- `Overall Quality` [gauge]: populated, `0.00%`
- `Manifest Write Failures` [stat]: explicit zero-state
- `Ledger Append Failures` [stat]: explicit zero-state
- `Checkpoint Incompatibilities` [stat]: explicit zero-state
- `Lineage Refs Missing` [stat]: explicit zero-state
- `Control-plane Lookup Failures` [stat]: explicit zero-state
- `Control-plane Lookup p95` [stat]: populated, `0 s`
- `Silver Filter Rejects` [stat]: populated, about `10k`
- `Silver Filter Reject Rate` [gauge]: populated, about `5.09%`
- `Lineage Fragment Outcomes` [timeseries]: populated

Findings:

- no broken or empty core panels remain
- zero-state control-plane panels now render as usable values instead of `No data`
- `Overall Quality = 0.00%` is not a dashboard bug: this panel is defined as `gold / bronze`
- the panel aligns with current live flow, where Bronze is populated, `Silver Filter Rejects` are high, and Gold is currently `0`

Recommendations:

- no corrective dashboard action required
- retain current zero-state rendering as the baseline
- investigate why the current selected run window has no Gold output

### 2. Data Quality

Dashboard file: [bioetl-dq-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-dq-v2.json)
Screenshot: [bioetl-dq-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-dq-v2.png)

Overall status: Healthy dashboard with downstream completion gap
Confidence: High

Verified panels:

- `Pipeline` [text]: populated, `chembl_activity`
- `Execution Timestamp` [stat]: populated, `03/30/2026, 10:44:50 AM`
- `Data Flow: Bronze -> Silver -> Gold` [timeseries]: populated
- `Data Quality Score` [gauge]: populated, `100.0%`
- `Source Records (Bronze)` [stat]: populated, about `50k`
- `Clean Records (Gold)` [stat]: populated, `0`
- `DQ Validation Score` [gauge]: populated, `100.0%`
- `Records Quarantined` [stat]: explicit zero-state
- `Soft Threshold Exceeded` [stat]: explicit zero-state
- `Data Freshness Lag (seconds)` [gauge]: populated, about `1 hours`
- `Silver Filter Rejects` [stat]: populated, about `10k`
- `Silver Filter Rejects by Pipeline` [bargauge]: populated, single-series view around `10.2k`
- `Quarantine by Error Type` [piechart]: explicit placeholder / zero-state
- `Anomalies Detected` [timeseries]: explicit zero-state
- `DQ Check Duration (p95)` [timeseries]: explicit zero-state
- `Silver Validation Failures` [stat]: explicit zero-state
- `Lineage Refs Missing` [stat]: explicit zero-state

Findings:

- previously empty DQ zero-state panels now render correctly
- `Quarantine by Error Type`, `Anomalies Detected`, and `DQ Check Duration (p95)` no longer disappear into `No data`
- `Data Quality Score = 100%` and `DQ Validation Score = 100%` are not inconsistent with `Clean Records (Gold) = 0`: these gauges are backed by validation score metrics, not by Gold throughput
- the dashboard therefore looks structurally correct, but the live pipeline state indicates that nothing reached Gold in the selected window
- `Silver Filter Rejects by Pipeline` is technically populated but visually weak because the current window only has one dominant series

Recommendations:

- no critical corrective dashboard action required
- optional UX improvement: make `Silver Filter Rejects by Pipeline` easier to read when only one series is present
- investigate why Gold remains `0` while Bronze and Silver activity are present

### 3. Provider Health

Dashboard file: [bioetl-provider-health-v2.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-provider-health-v2.json)
Screenshot: [bioetl-provider-health-v2.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-provider-health-v2.png)

Overall status: Healthy
Confidence: High

Verified panels:

- `Health Check Latency by Provider (p95)` [timeseries]: populated
- `Healthy Checks` [stat]: populated, `3`
- `Health Checks Total` [stat]: populated, `3`
- `Degraded Checks` [stat]: populated, `0`
- `Provider Failure Rate` [gauge]: populated, `0.00%`
- `Provider Health Check Latency (p95) - $provider` [gauge]: populated, about `9.500 ms`

Findings:

- earlier counter/latency inconsistency is no longer present in the live view
- the dashboard now presents a coherent provider-health story

Recommendations:

- no corrective action required

### 4. Runtime

Dashboard file: [bioetl-runtime.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/grafana/dashboards/bioetl-runtime.json)
Screenshot: [bioetl-runtime.png](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/output/playwright/bioetl-runtime.png)

Overall status: Healthy with one live alert signal to investigate
Confidence: High

Verified panels:

- `Runtime Scope` [text]: populated, wide multi-pipeline scope
- `Warnings` [stat]: explicit zero-state
- `Unstructured Logs` [stat]: explicit zero-state
- `DQ Alert Conditions` [stat]: explicit zero-state
- `Control-plane Alert Conditions` [stat]: explicit zero-state
- `Provider Alert Conditions` [stat]: explicit zero-state
- `Freshness Alert Conditions` [stat]: populated, `2`
- `Pipeline Alert Conditions` [stat]: explicit zero-state
- `Top Warning Events` [bargauge]: explicit placeholder / zero-state
- `Log Hygiene Trend` [stat summary]: explicit zero-state
- `Trace-enabled Runs` [stat]: explicit zero-state
- `Silver Filter Rejects` [stat]: populated, about `10.2k`
- `DQ Context Failures` [stat]: explicit zero-state
- `DQ Reports Skipped` [stat]: populated, `2`
- `DQ Reports Generated` [stat]: populated, `2`
- `Control-plane Lookup Outcomes` [timeseries]: explicit placeholder / zero-state
- `Control-plane Lookup p95` [stat]: populated, `0 s`

Findings:

- all previously broken runtime zero-state panels now render usable values
- `Warnings`, `Unstructured Logs`, `Top Warning Events`, `Log Hygiene Trend`, and `Control-plane Lookup Outcomes` no longer collapse into empty / `No data` panels
- `Freshness Alert Conditions = 2` is a live signal, not a rendering bug
- the current runtime scope is broad, so the freshness count is not limited to one pipeline
- `DQ Reports Skipped = 2` and `DQ Reports Generated = 2` are also live signals, not visualization defects

Recommendations:

- do not treat `Freshness Alert Conditions = 2` as a dashboard bug
- follow up operationally on the freshness alert source if this dashboard is expected to stay clean
- optionally tighten dashboard defaults if the intended default scope is a single pipeline rather than `All`

## Summary Table

| Dashboard | Status | Panels | Problems | Criticality | Brief conclusion |
|---|---|---:|---:|---|---|
| `bioetl-overview-v2` | Healthy dashboard with live pipeline degradation signal | 16 | 0 dashboard bugs, 1 live operational issue | Medium | Dashboard is correct, but Gold output is absent in the selected live window. |
| `bioetl-dq-v2` | Healthy dashboard with downstream completion gap | 17 | 0 dashboard bugs, 1 cosmetic, 1 live operational issue | Medium | DQ rendering is fixed; live data still shows Bronze activity without Gold completion. |
| `bioetl-provider-health-v2` | Healthy | 6 | 0 | Low | Provider counters and latency views are now consistent. |
| `bioetl-runtime` | Healthy with one live alert signal to investigate | 17 | 0 dashboard bugs, 1 live alert condition | Medium | Runtime rendering issues are fixed; remaining signal is operational, not visual. |

## Final Conclusion

- All four shipped dashboards were reviewed against live Grafana renders.
- The dashboard-filling problems identified earlier were primarily zero-state rendering issues, and those have now been corrected.
- `bioetl-provider-health-v2` is in a good operational state.
- `bioetl-overview-v2` and `bioetl-dq-v2` are visually correct, but the current live telemetry shows a real downstream completion gap: Bronze is populated while Gold remains `0`.
- `bioetl-runtime` is also visually healthy; the remaining notable item is the live `Freshness Alert Conditions = 2` signal, which should be handled as runtime telemetry, not as a dashboard defect.
