# Panel Title Inventory

Generated from `grafana/dashboards/*.json`.

## KPI ownership contract anchors

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (`kpi_ownership`).

| KPI key | Canonical UID | Mirror panel(s) |
|---|---|---|
| `failed_runs_in_range` | `bioetl-overview-v2` | `bioetl-runtime#205` |
| `worst_lag_stage` | `bioetl-overview-v2` | `bioetl-runtime#237` |
| `worst_backlog_stage` | `bioetl-overview-v2` | `bioetl-runtime#238` |

| Dashboard | Panel ID | Title |
|---|---:|---|
| bioetl-control-plane-v1.json | 1 | Monitor: Manifest Write Failures |
| bioetl-control-plane-v1.json | 2 | Monitor: Ledger Append Failures |
| bioetl-control-plane-v1.json | 3 | Monitor: Checkpoint Incompatibilities |
| bioetl-control-plane-v1.json | 4 | Monitor: GLOBAL Control-Plane Read Failures |
| bioetl-control-plane-v1.json | 5 | Track: Checkpoint Compatibility Outcomes |
| bioetl-control-plane-v1.json | 6 | Track: GLOBAL Control-Plane Reads by Store / Operation / Status |
| bioetl-control-plane-v1.json | 7 | Track: Ledger Appends by Event Type / Status |
| bioetl-control-plane-v1.json | 101 | Monitor: Checkpoint Load Failures |
| bioetl-control-plane-v1.json | 102 | Monitor: Checkpoint Save Failures |
| bioetl-control-plane-v1.json | 103 | Monitor: GLOBAL Checkpoint Operator Failures |
| bioetl-control-plane-v1.json | 104 | Monitor: Replay Not Reconstructable |
| bioetl-control-plane-v1.json | 105 | Track: Checkpoint Save Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 106 | Track: GLOBAL Checkpoint Operator Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 107 | Track: GLOBAL Audit Write Outcomes |
| bioetl-control-plane-v1.json | 108 | Track: GLOBAL Audit Query Outcomes |
| bioetl-control-plane-v1.json | 109 | Track: GLOBAL Audit Write Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 110 | Track: GLOBAL Audit Query Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 111 | Track: GLOBAL Control-Plane Read Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 112 | Track: Lineage Fragment Outcomes |
| bioetl-control-plane-v1.json | 120 | Monitor: Replay Drift |
| bioetl-control-plane-v1.json | 121 | Track: Replay Lag Seconds |
| bioetl-control-plane-v1.json | 122 | Monitor: Lineage Refs Missing |
| bioetl-control-plane-v1.json | 130 | Track: Replay / Resume Blockers in Range |
| bioetl-control-plane-v1.json | 131 | Track: Manifest Writes by Status |
| bioetl-control-plane-v1.json | 132 | Monitor: Manifest Write Failure Ratio Severity |
| bioetl-control-plane-v1.json | 133 | Monitor: Ledger Append Failure Ratio Severity |
| bioetl-control-plane-v1.json | 134 | Track: Replay Drift by Type |
| bioetl-control-plane-v1.json | 135 | Track: Replay Lag Trend |
| bioetl-control-plane-v1.json | 136 | Monitor: GLOBAL Control-Plane Read Failure Ratio Severity |
| bioetl-control-plane-v1.json | 137 | Monitor: Lineage Fragment Persistence Failures |
| bioetl-control-plane-v1.json | 138 | Inspect: Missing Lineage Refs by Layer / Type |
| bioetl-control-plane-v1.json | 139 | Review: Remaining Replay-Safety Signals |
| bioetl-control-plane-v1.json | 891 | Monitor: Replay Safety State |
| bioetl-control-plane-v1.json | 892 | Inspect: Checkpoint Freshness Gap |
| bioetl-control-plane-v1.json | 893 | Monitor: Manifest / Ledger Integrity |
| bioetl-control-plane-v1.json | 894 | Inspect: Known Blind Spots |
| bioetl-control-plane-v1.json | 908 | Inspect: Terminal Run Events by Status in Range |
| bioetl-control-plane-v1.json | 9400 | Provenance |
| bioetl-control-plane-v1.json | 9401 | Status |
| bioetl-control-plane-v1.json | 9402 | ID |
| bioetl-control-plane-v1.json | 9403 | Processed Records |
| bioetl-control-plane-v1.json | 9404 | Inspect: P0 Identity Anchors |
| bioetl-control-plane-v1.json | 9405 | Inspect: Identity Gaps |
| bioetl-control-plane-v1.json | 9406 | Inspect: Checkpoint Anchor Compare |
| bioetl-control-plane-v1.json | 9407 | Inspect: Copyable Identity Handoffs |
| bioetl-dq-v2.json | 1 | Track Range Evidence: Bronze -> Silver -> Gold |
| bioetl-dq-v2.json | 2 | Data Quality Score (Volume-weighted) |
| bioetl-dq-v2.json | 3 | Source Records in Range (Bronze) |
| bioetl-dq-v2.json | 4 | Clean Records in Range (Gold) |
| bioetl-dq-v2.json | 5 | Worst-Entity DQ Score |
| bioetl-dq-v2.json | 6 | Records Quarantined |
| bioetl-dq-v2.json | 7 | Soft Threshold Exceeded |
| bioetl-dq-v2.json | 8 | Worst Data Freshness Lag (seconds) |
| bioetl-dq-v2.json | 9 | Quarantine by Error Type |
| bioetl-dq-v2.json | 10 | Anomalies Detected |
| bioetl-dq-v2.json | 11 | DQ Check Duration (p95) |
| bioetl-dq-v2.json | 12 | Silver Validation Failures |
| bioetl-dq-v2.json | 99 | Pipeline |
| bioetl-dq-v2.json | 9100 | Monitor DQ Current Status |
| bioetl-dq-v2.json | 9101 | Monitor DQ Threshold State |
| bioetl-dq-v2.json | 9102 | Inspect DQ Current Reasons |
| bioetl-dq-v2.json | 9103 | Review: First Action |
| bioetl-dq-v2.json | 9400 | Provenance |
| bioetl-dq-v2.json | 9401 | Status |
| bioetl-dq-v2.json | 9402 | ID |
| bioetl-dq-v2.json | 9403 | Processed Records |
| bioetl-dq-v2.json | 101 | Latest Successful Data Timestamp |
| bioetl-dq-v2.json | 116 | Review: Lineage Handoff to Control Plane |
| bioetl-dq-v2.json | 117 | Silver Filter Rejects |
| bioetl-dq-v2.json | 118 | Silver Filter Rejects by Pipeline |
| bioetl-dq-v2.json | 121 | Top Silver Reject Reasons (Pareto) |
| bioetl-dq-v2.json | 122 | Top Silver Reject Fields |
| bioetl-dq-v2.json | 150 | Review: Aggregate Control-plane Handoff |
| bioetl-dq-v2.json | 151 | Gold Strict Validation Failures |
| bioetl-dq-v2.json | 152 | Silver Filter Reject Accounting Mismatch |
| bioetl-dq-v2.json | 153 | Data Quality Score Trend (Volume-weighted) |
| bioetl-dq-v2.json | 154 | DQ Impact on Deliverability (Blocked Share) |
| bioetl-dq-v2.json | 155 | DQ Impact on Deliverability Trend (Blocked Share %) |
| bioetl-overview-v2.json | 99 | Provenance |
| bioetl-overview-v2.json | 214 | Status |
| bioetl-overview-v2.json | 215 | First Action |
| bioetl-overview-v2.json | 1000 | Navigation |
| bioetl-overview-v2.json | 9002 | Inputs |
| bioetl-overview-v2.json | 9003 | Runtime |
| bioetl-overview-v2.json | 9004 | Data Quality |
| bioetl-overview-v2.json | 9005 | Data Validation |
| bioetl-overview-v2.json | 9006 | Control Plane |
| bioetl-overview-v2.json | 9007 | Provider |
| bioetl-overview-v2.json | 9009 | Range Evidence (Historical / Recent History) |
| bioetl-overview-v2.json | 9010 | Historical Failures |
| bioetl-overview-v2.json | 9011 | Recent Terminal Runs |
| bioetl-overview-v2.json | 9012 | Diagnostics & Docs (Logs / Traces / Raw Metrics) |
| bioetl-overview-v2.json | 9013 | Workflow |
| bioetl-overview-v2.json | 9014 | L1 Historical Trends |
| bioetl-overview-v2.json | 9015 | Silver Rejects + Rate |
| bioetl-overview-v2.json | 9018 | Runtime Blockers Trend |
| bioetl-overview-v2.json | 9019 | DQ Status Trend |
| bioetl-overview-v2.json | 9020 | Gold Lifecycle Trend |
| bioetl-overview-v2.json | 9021 | Diagnostics Navigation |
| bioetl-overview-v2.json | 9300 | ID |
| bioetl-overview-v2.json | 9301 | Processed Records |
| bioetl-provider-health-v2.json | 1 | Track Health Check Latency by Provider (p95) |
| bioetl-provider-health-v2.json | 2 | Monitor Healthy Checks (Selected Range) |
| bioetl-provider-health-v2.json | 7 | Track Health Checks Total (Selected Range) |
| bioetl-provider-health-v2.json | 31 | Monitor Cross-Scope Adapter Circuit Breaker State (max) |
| bioetl-provider-health-v2.json | 32 | Track Cross-Scope Adapter Circuit Breaker Trips |
| bioetl-provider-health-v2.json | 102 | Inspect Provider Health Check Latency (p95) - $provider |
| bioetl-provider-health-v2.json | 104 | Track Provider Failure Rate (Selected Range) |
| bioetl-provider-health-v2.json | 105 | Monitor Degraded Checks (Selected Range) |
| bioetl-provider-health-v2.json | 106 | Track Failure and Degraded Trend by Provider |
| bioetl-provider-health-v2.json | 107 | Track Provider Failure Share (Selected Range) |
| bioetl-provider-health-v2.json | 108 | Track Retries Exhausted by Provider/Operation |
| bioetl-provider-health-v2.json | 109 | Track Retries Exhausted Trend by Provider/Operation |
| bioetl-provider-health-v2.json | 110 | Inspect Adapter Request Latency by Endpoint (p95) |
| bioetl-provider-health-v2.json | 111 | Inspect HTTP Errors by Method/Error Type |
| bioetl-provider-health-v2.json | 112 | Track Rate Limiter Wait by Provider (p95) |
| bioetl-provider-health-v2.json | 113 | Monitor Minimum Rate Limiter Tokens Available |
| bioetl-provider-health-v2.json | 114 | Monitor Current Provider Health Status |
| bioetl-provider-health-v2.json | 9002 | First Action |
| bioetl-provider-health-v2.json | 9100 | GLOBAL Provider Scope |
| bioetl-provider-health-v2.json | 9101 | Monitor GLOBAL Provider Severity Matrix |
| bioetl-provider-health-v2.json | 9102 | Inspect Critical Providers |
| bioetl-provider-health-v2.json | 9103 | Inspect Provider Top Causes |
| bioetl-provider-health-v2.json | 9104 | Monitor Provider Telemetry Freshness |
| bioetl-provider-health-v2.json | 9400 | Provenance |
| bioetl-provider-health-v2.json | 9401 | Status |
| bioetl-provider-health-v2.json | 9402 | ID |
| bioetl-provider-health-v2.json | 9403 | Processed Records |
| bioetl-runtime.json | 4 | Inspect DQ Alert Conditions |
| bioetl-runtime.json | 5 | Inspect Control-plane Alert Conditions |
| bioetl-runtime.json | 6 | Inspect GLOBAL Provider Alert Conditions |
| bioetl-runtime.json | 7 | Inspect Freshness Alert Conditions |
| bioetl-runtime.json | 16 | Monitor Runtime Blockers |
| bioetl-runtime.json | 9100 | Runtime Status |
| bioetl-runtime.json | 9101 | Runtime Blockers |
| bioetl-runtime.json | 9102 | Runtime Telemetry Gap |
| bioetl-runtime.json | 21 | Monitor Memory Pressure Active |
| bioetl-runtime.json | 205 | Failed Runs |
| bioetl-runtime.json | 207 | Track Pipeline Phase Duration p50/p95/p99 |
| bioetl-runtime.json | 209 | Track GLOBAL Shutdown Initiated by Reason / Interval |
| bioetl-runtime.json | 210 | Track GLOBAL Shutdown Completed by Reason / Interval |
| bioetl-runtime.json | 220 | Runtime Error Rate |
| bioetl-runtime.json | 230 | Monitor Pipeline Alert Conditions |
| bioetl-runtime.json | 236 | Monitor No-Records Runs |
| bioetl-runtime.json | 237 | Worst Stage Lag |
| bioetl-runtime.json | 238 | Track Stage Backlog Trend |
| bioetl-runtime.json | 239 | Track Pipeline Duration p50/p95/p99 |
| bioetl-runtime.json | 240 | Track Records by Stage / Interval |
| bioetl-runtime.json | 241 | Track Records by Stage / Run Type / Range |
| bioetl-runtime.json | 242 | Inspect Active Runtime Blocker Detail |
| bioetl-runtime.json | 243 | Inspect Stage Expectedness |
| bioetl-runtime.json | 250 | Inspect Warning Logs |
| bioetl-runtime.json | 251 | Inspect GLOBAL Unstructured Logs |
| bioetl-runtime.json | 256 | Inspect Errors by Stage / Error Code / Range |
| bioetl-runtime.json | 257 | Inspect Top Warning Events by Message / Range |
| bioetl-runtime.json | 258 | Track GLOBAL Log Hygiene Trend |
| bioetl-runtime.json | 9400 | Provenance |
| bioetl-runtime.json | 9401 | Status |
| bioetl-runtime.json | 9402 | ID |
| bioetl-runtime.json | 9403 | Processed Records |
| bioetl-runtime.json | 9991 | First Action |
| bioetl-silver-reject-explorer.json | 1 | Inspect Explorer Scope |
| bioetl-silver-reject-explorer.json | 13 | Monitor Explorer Backend Health |
| bioetl-silver-reject-explorer.json | 10 | Review: First Action / No-Data Semantics |
| bioetl-silver-reject-explorer.json | 2 | Monitor Filtered Records Total |
| bioetl-silver-reject-explorer.json | 3 | Track Reject Rate vs Bronze |
| bioetl-silver-reject-explorer.json | 4 | Inspect Run Scope Summary |
| bioetl-silver-reject-explorer.json | 5 | Inspect Top Reject Reasons |
| bioetl-silver-reject-explorer.json | 6 | Inspect Top Reject Fields |
| bioetl-silver-reject-explorer.json | 7 | Inspect Top Reason Signatures |
| bioetl-silver-reject-explorer.json | 8 | Inspect Filtered Records Table |
| bioetl-silver-reject-explorer.json | 9 | Inspect Selected Record Details |
| bioetl-workflow-overview.json | 1 | Failed Workflow Runs / Range |
| bioetl-workflow-overview.json | 2 | Failed Workflow Runs / Range |
| bioetl-workflow-overview.json | 3 | Failed Pipeline Steps / Range |
| bioetl-workflow-overview.json | 4 | Workflow Run Outcomes / Range |
| bioetl-workflow-overview.json | 5 | Step Outcomes by Kind / Step Status / Range |
| bioetl-workflow-overview.json | 6 | Failed Transform Steps / Range |
| bioetl-workflow-overview.json | 7 | Skipped Step Events / Range |
| bioetl-workflow-overview.json | 8 | Step Duration p95 by Kind / Step Status / Range |
| bioetl-workflow-overview.json | 9 | First Action |
| bioetl-workflow-overview.json | 9400 | Provenance |
| bioetl-workflow-overview.json | 9401 | Status |
| bioetl-workflow-overview.json | 9402 | ID |
| bioetl-workflow-overview.json | 9403 | Processed Records |
