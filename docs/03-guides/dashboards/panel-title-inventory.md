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
| --- | ---: | --- |
| bioetl-control-plane-v1.json | 1000 | Navigation |
| bioetl-control-plane-v1.json | 9400 | Provenance |
| bioetl-control-plane-v1.json | 9401 | Status |
| bioetl-control-plane-v1.json | 906 | Next Action: Replay Diagnostics |
| bioetl-control-plane-v1.json | 891 | Monitor: Replay Safety State |
| bioetl-control-plane-v1.json | 892 | Monitor: Checkpoint Freshness Lag (seconds) |
| bioetl-control-plane-v1.json | 893 | Monitor: Manifest / Ledger Integrity |
| bioetl-control-plane-v1.json | 907 | Inspect: Telemetry Missing |
| bioetl-control-plane-v1.json | 902 | Incident Drilldown: Replay Safety (Checkpoint / Replay) |
| bioetl-control-plane-v1.json | 894 | Inspect: Known Blind Spots |
| bioetl-control-plane-v1.json | 130 | Track: Replay / Resume Blockers in Range |
| bioetl-control-plane-v1.json | 3 | Monitor: Checkpoint Incompatibilities |
| bioetl-control-plane-v1.json | 104 | Monitor: Replay Not Reconstructable |
| bioetl-control-plane-v1.json | 120 | Monitor: Replay Drift |
| bioetl-control-plane-v1.json | 101 | Monitor: Checkpoint Load Failures |
| bioetl-control-plane-v1.json | 102 | Monitor: Checkpoint Save Failures |
| bioetl-control-plane-v1.json | 103 | Monitor: GLOBAL Checkpoint Operator Failures |
| bioetl-control-plane-v1.json | 121 | Track: Replay Lag Seconds |
| bioetl-control-plane-v1.json | 5 | Track: Checkpoint Compatibility Outcomes |
| bioetl-control-plane-v1.json | 134 | Track: Replay Drift by Type |
| bioetl-control-plane-v1.json | 135 | Track: Replay Lag Trend |
| bioetl-control-plane-v1.json | 105 | Track: Checkpoint Save Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 106 | Track: GLOBAL Checkpoint Operator Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 901 | Incident Drilldown: Manifest / Ledger Integrity |
| bioetl-control-plane-v1.json | 908 | Inspect: Terminal Run Events by Status in Range |
| bioetl-control-plane-v1.json | 1 | Monitor: Manifest Write Failures |
| bioetl-control-plane-v1.json | 2 | Monitor: Ledger Append Failures |
| bioetl-control-plane-v1.json | 131 | Track: Manifest Writes by Status |
| bioetl-control-plane-v1.json | 7 | Track: Ledger Appends by Event Type / Status |
| bioetl-control-plane-v1.json | 132 | Monitor: Manifest Write Failure Ratio |
| bioetl-control-plane-v1.json | 133 | Monitor: Ledger Append Failure Ratio |
| bioetl-control-plane-v1.json | 903 | Incident Drilldown: Global Control-Plane Store Reliability |
| bioetl-control-plane-v1.json | 4 | Monitor: GLOBAL Control-Plane Read Failures |
| bioetl-control-plane-v1.json | 136 | Monitor: GLOBAL Control-Plane Read Failure Ratio Severity |
| bioetl-control-plane-v1.json | 6 | Track: GLOBAL Control-Plane Reads by Store / Operation / Status |
| bioetl-control-plane-v1.json | 111 | Track: GLOBAL Control-Plane Read Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 904 | Incident Drilldown: Audit / Lineage Completeness |
| bioetl-control-plane-v1.json | 122 | Monitor: Lineage Refs Missing |
| bioetl-control-plane-v1.json | 137 | Monitor: Lineage Fragment Persistence Failures |
| bioetl-control-plane-v1.json | 138 | Inspect: Missing Lineage Refs by Layer / Type |
| bioetl-control-plane-v1.json | 107 | Track: GLOBAL Audit Write Outcomes |
| bioetl-control-plane-v1.json | 108 | Track: GLOBAL Audit Query Outcomes |
| bioetl-control-plane-v1.json | 109 | Track: GLOBAL Audit Write Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 110 | Track: GLOBAL Audit Query Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 112 | Track: Lineage Fragment Outcomes |
| bioetl-control-plane-v1.json | 905 | Identity evidence and remaining replay-safety signals |
| bioetl-control-plane-v1.json | 9407 | Inspect: Copyable Identity Handoffs |
| bioetl-control-plane-v1.json | 9404 | Inspect: Overview Identity Anchors |
| bioetl-control-plane-v1.json | 9410 | ID Empty State |
| bioetl-control-plane-v1.json | 9411 | Processed Records Empty State |
| bioetl-control-plane-v1.json | 9405 | Inspect: Identity Gaps |
| bioetl-control-plane-v1.json | 9406 | Inspect: Checkpoint Anchor Compare |
| bioetl-control-plane-v1.json | 9408 | Inspect: P1 Replay and Evidence Anchors |
| bioetl-control-plane-v1.json | 9409 | Inspect: P2 Forensic Anchors |
| bioetl-control-plane-v1.json | 139 | Review: Remaining Replay-Safety Signals |
| bioetl-control-plane-v1.json | 9412 | Run context (thin) → Run Explorer |
| bioetl-control-plane-v1.json | 9402 | ID |
| bioetl-control-plane-v1.json | 9403 | Processed Records |
| bioetl-dq-v2.json | 1000 | Navigation |
| bioetl-dq-v2.json | 9400 | Provenance |
| bioetl-dq-v2.json | 9401 | Status |
| bioetl-dq-v2.json | 9103 | Review: First Action |
| bioetl-dq-v2.json | 9101 | Monitor DQ Threshold State |
| bioetl-dq-v2.json | 9102 | Inspect DQ Current Reasons |
| bioetl-dq-v2.json | 8 | Time Range · Worst Freshness Age (hours; SLA 24/72) |
| bioetl-dq-v2.json | 154 | Track: DQ Blocked Records in Range (Evidence) |
| bioetl-dq-v2.json | 220 | Run lane · Silver/Gold rejects |
| bioetl-dq-v2.json | 152 | Monitor: Silver Filter Reject Accounting Mismatch |
| bioetl-dq-v2.json | 121 | Inspect: Top Silver Reject Reasons (Pareto) |
| bioetl-dq-v2.json | 122 | Inspect: Top Silver Reject Fields |
| bioetl-dq-v2.json | 118 | Inspect: Silver Filter Rejects by Pipeline |
| bioetl-dq-v2.json | 156 | Inspect: Gold Reject Outcomes by Pipeline |
| bioetl-dq-v2.json | 221 | Now lane · validation diagnostics |
| bioetl-dq-v2.json | 1 | Track Range Evidence: Bronze -> Silver -> Gold |
| bioetl-dq-v2.json | 3 | Track: Source Records in Range (Bronze) |
| bioetl-dq-v2.json | 4 | Track: Clean Records in Range (Gold) |
| bioetl-dq-v2.json | 7 | Track: Silver Validation Failures in Range |
| bioetl-dq-v2.json | 101 | Review: Latest Successful Data Timestamp |
| bioetl-dq-v2.json | 9 | Inspect: Quarantine by Error Type |
| bioetl-dq-v2.json | 12 | Monitor: Silver Validation Failures |
| bioetl-dq-v2.json | 151 | Monitor: Gold Strict Validation Failures |
| bioetl-dq-v2.json | 10 | Track: Anomalies Detected |
| bioetl-dq-v2.json | 11 | Track: DQ Check Duration (p95) |
| bioetl-dq-v2.json | 155 | Track: DQ Threshold Events in Range Trend |
| bioetl-dq-v2.json | 153 | Track: Data Quality Score Trend (Volume-weighted) |
| bioetl-dq-v2.json | 116 | Review: Lineage Handoff to Control Plane |
| bioetl-dq-v2.json | 150 | Review: Aggregate Control-plane Handoff |
| bioetl-dq-v2.json | 9404 | Range lane · debug evidence |
| bioetl-dq-v2.json | 2 | Monitor: Data Quality Score (Volume-weighted) |
| bioetl-dq-v2.json | 5 | Monitor: Worst-Entity DQ Score |
| bioetl-dq-v2.json | 6 | Track: Records Quarantined in Range |
| bioetl-dq-v2.json | 117 | Track: Silver Filter Rejects in Range |
| bioetl-dq-v2.json | 9405 | Run context (thin) → Run Explorer |
| bioetl-dq-v2.json | 9402 | ID |
| bioetl-dq-v2.json | 9403 | Processed Records |
| bioetl-overview-v2.json | 9600 | Alert/SLO Triage |
| bioetl-overview-v2.json | 9601 | Triage Alert State |
| bioetl-overview-v2.json | 1000 | Navigation |
| bioetl-overview-v2.json | 99 | Provenance |
| bioetl-overview-v2.json | 214 | Status |
| bioetl-overview-v2.json | 215 | First Action |
| bioetl-overview-v2.json | 9002 | Inputs |
| bioetl-overview-v2.json | 9014 | L1 Historical Trends |
| bioetl-overview-v2.json | 9018 | Runtime Blockers Trend |
| bioetl-overview-v2.json | 9019 | DQ Status Trend |
| bioetl-overview-v2.json | 9020 | Gold Lifecycle Trend |
| bioetl-overview-v2.json | 9009 | Range Evidence (Historical / Recent History) |
| bioetl-overview-v2.json | 9010 | Historical Failures |
| bioetl-overview-v2.json | 9011 | Recent Terminal Runs |
| bioetl-overview-v2.json | 9015 | Silver Rejects + Rate |
| bioetl-overview-v2.json | 9012 | Diagnostics & Docs (Logs / Traces / Raw Metrics) |
| bioetl-overview-v2.json | 9021 | Diagnostics Navigation |
| bioetl-overview-v2.json | 9006 | Control Plane |
| bioetl-overview-v2.json | 9003 | Runtime |
| bioetl-overview-v2.json | 9004 | Data Quality |
| bioetl-overview-v2.json | 9007 | Provider |
| bioetl-overview-v2.json | 9005 | Data Validation |
| bioetl-overview-v2.json | 9013 | Workflow |
| bioetl-overview-v2.json | 9602 | Run context (thin) → Run Explorer |
| bioetl-overview-v2.json | 9300 | ID |
| bioetl-overview-v2.json | 9301 | Processed Records |
| bioetl-provider-health-v2.json | 1000 | Navigation |
| bioetl-provider-health-v2.json | 9400 | Provenance |
| bioetl-provider-health-v2.json | 9401 | Status |
| bioetl-provider-health-v2.json | 9002 | First Action |
| bioetl-provider-health-v2.json | 9101 | Monitor GLOBAL Provider Severity Matrix |
| bioetl-provider-health-v2.json | 9102 | Inspect Critical Providers |
| bioetl-provider-health-v2.json | 9103 | Inspect Provider Top Causes |
| bioetl-provider-health-v2.json | 9104 | Monitor Provider Telemetry Freshness |
| bioetl-provider-health-v2.json | 91 | Selected Provider Detail |
| bioetl-provider-health-v2.json | 106 | Track Failure and Degraded Trend by Provider |
| bioetl-provider-health-v2.json | 107 | Track Provider Failure Share (Selected Range) |
| bioetl-provider-health-v2.json | 108 | Track Retries Exhausted by Provider/Operation |
| bioetl-provider-health-v2.json | 109 | Track Retries Exhausted Trend by Provider/Operation |
| bioetl-provider-health-v2.json | 102 | Inspect Provider Health Check Latency (p95) - $provider |
| bioetl-provider-health-v2.json | 110 | Inspect Adapter Request Latency by Endpoint (p95) |
| bioetl-provider-health-v2.json | 111 | Inspect Rate Limit Errors by Method |
| bioetl-provider-health-v2.json | 115 | Inspect Network Timeout Errors by Method |
| bioetl-provider-health-v2.json | 112 | Track Rate Limiter Wait by Provider (p95) |
| bioetl-provider-health-v2.json | 113 | Monitor Minimum Rate Limiter Tokens Available |
| bioetl-provider-health-v2.json | 31 | Monitor Cross-Scope Adapter Circuit Breaker State (max) |
| bioetl-provider-health-v2.json | 32 | Track Cross-Scope Adapter Circuit Breaker Trips |
| bioetl-provider-health-v2.json | 9404 | Range / debug evidence |
| bioetl-provider-health-v2.json | 114 | Review Raw Provider Health Enum |
| bioetl-provider-health-v2.json | 1 | Track Health Check Latency by Provider (p95) |
| bioetl-provider-health-v2.json | 2 | Monitor Healthy Checks (Selected Range) |
| bioetl-provider-health-v2.json | 105 | Monitor Degraded Checks (Selected Range) |
| bioetl-provider-health-v2.json | 104 | Track Provider Failure Rate (Selected Range) |
| bioetl-provider-health-v2.json | 7 | Track Health Checks Total (Selected Range) |
| bioetl-provider-health-v2.json | 9405 | Run context (thin) → Run Explorer |
| bioetl-provider-health-v2.json | 9402 | ID |
| bioetl-provider-health-v2.json | 9403 | Processed Records |
| bioetl-runtime.json | 1000 | Navigation |
| bioetl-runtime.json | 9400 | Provenance |
| bioetl-runtime.json | 9401 | Status |
| bioetl-runtime.json | 9991 | First Action |
| bioetl-runtime.json | 9101 | Runtime Blockers |
| bioetl-runtime.json | 220 | Runtime Error Rate |
| bioetl-runtime.json | 9102 | Runtime Telemetry Gap |
| bioetl-runtime.json | 252 | Detect |
| bioetl-runtime.json | 243 | Inspect Stage Expectedness |
| bioetl-runtime.json | 238 | Track Stage Backlog Trend |
| bioetl-runtime.json | 240 | Track Records by Stage / Interval |
| bioetl-runtime.json | 242 | Inspect Active Runtime Blocker Detail |
| bioetl-runtime.json | 253 | Localize |
| bioetl-runtime.json | 207 | Track Pipeline Phase Duration p50/p95/p99 |
| bioetl-runtime.json | 239 | Track Pipeline Duration p50/p95/p99 |
| bioetl-runtime.json | 256 | Inspect Errors by Stage / Error Code / Range |
| bioetl-runtime.json | 241 | Track Records by Stage / Run Type / Range |
| bioetl-runtime.json | 254 | Escalate |
| bioetl-runtime.json | 2541 | Review Runtime-owned escalation |
| bioetl-runtime.json | 230 | Monitor Pipeline Alert Conditions |
| bioetl-runtime.json | 236 | Monitor No-Records Runs |
| bioetl-runtime.json | 21 | Monitor Memory Pressure Active |
| bioetl-runtime.json | 2542 | Review Cross-domain handoffs |
| bioetl-runtime.json | 4 | Inspect DQ Alert Conditions |
| bioetl-runtime.json | 5 | Inspect Control-plane Alert Conditions |
| bioetl-runtime.json | 6 | Inspect Provider Alert Conditions |
| bioetl-runtime.json | 259 | Inspect GLOBAL Provider Alert Conditions |
| bioetl-runtime.json | 7 | Inspect Freshness Lagged Entities >24h |
| bioetl-runtime.json | 2543 | Review Process-level signals (GLOBAL) |
| bioetl-runtime.json | 209 | Track GLOBAL Shutdown Initiated by Reason / Interval |
| bioetl-runtime.json | 210 | Track GLOBAL Shutdown Completed by Reason / Interval |
| bioetl-runtime.json | 9992 | Runtime secondary KPIs |
| bioetl-runtime.json | 237 | Worst Stage Lag |
| bioetl-runtime.json | 16 | Monitor Runtime Blockers |
| bioetl-runtime.json | 205 | Failed Runs |
| bioetl-runtime.json | 9993 | Run context (thin) → Run Explorer |
| bioetl-runtime.json | 9402 | ID |
| bioetl-runtime.json | 9403 | Processed Records |
| bioetl-runtime.json | 9994 | Workflow band (merged from bioetl-workflow-overview) |
| bioetl-runtime.json | 9996 | Failed Workflow Runs / Range |
| bioetl-runtime.json | 9997 | Failed Pipeline Steps / Range |

## bioetl-incident-v1.json

| bioetl-incident-v1.json | 1000 | Navigation |
| bioetl-incident-v1.json | 9400 | Provenance |
| bioetl-incident-v1.json | 9401 | Status |
| bioetl-incident-v1.json | 2001 | Next Best Actions |
| bioetl-incident-v1.json | 2002 | Suspects · Runtime blockers |
| bioetl-incident-v1.json | 2003 | Suspects · Provider causes |
| bioetl-incident-v1.json | 2004 | Suspects · DQ reasons |
| bioetl-incident-v1.json | 2005 | Alert / Event Timeline (range) |

## bioetl-run-explorer-v1.json

| bioetl-run-explorer-v1.json | 1000 | Navigation |
| bioetl-run-explorer-v1.json | 1 | Run Scope |
| bioetl-run-explorer-v1.json | 9402 | ID |
| bioetl-run-explorer-v1.json | 9403 | Processed Records |
| bioetl-run-explorer-v1.json | 3001 | Next actions (≤4) |
