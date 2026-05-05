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
| bioetl-control-plane-v1.json | 1 | Manifest Write Failures |
| bioetl-control-plane-v1.json | 2 | Ledger Append Failures |
| bioetl-control-plane-v1.json | 3 | Checkpoint Incompatibilities |
| bioetl-control-plane-v1.json | 4 | GLOBAL Control-Plane Read Failures |
| bioetl-control-plane-v1.json | 5 | Checkpoint Compatibility Outcomes |
| bioetl-control-plane-v1.json | 6 | GLOBAL Control-Plane Reads by Store / Operation / Status |
| bioetl-control-plane-v1.json | 7 | Ledger Appends by Event Type / Status |
| bioetl-control-plane-v1.json | 101 | Checkpoint Load Failures |
| bioetl-control-plane-v1.json | 102 | Checkpoint Save Failures |
| bioetl-control-plane-v1.json | 103 | GLOBAL Checkpoint Operator Failures |
| bioetl-control-plane-v1.json | 104 | Replay Not Reconstructable |
| bioetl-control-plane-v1.json | 105 | Checkpoint Save Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 106 | GLOBAL Checkpoint Operator Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 107 | Audit Write Outcomes |
| bioetl-control-plane-v1.json | 108 | Audit Query Outcomes |
| bioetl-control-plane-v1.json | 109 | Audit Write Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 110 | Audit Query Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 111 | GLOBAL Control-Plane Read Latency p50/p95/p99 |
| bioetl-control-plane-v1.json | 112 | Lineage Fragment Outcomes |
| bioetl-control-plane-v1.json | 120 | Replay Drift |
| bioetl-control-plane-v1.json | 121 | Replay Lag Seconds |
| bioetl-control-plane-v1.json | 122 | Lineage Refs Missing |
| bioetl-control-plane-v1.json | 130 | Replay / Resume Blockers |
| bioetl-control-plane-v1.json | 131 | Manifest Writes by Status |
| bioetl-control-plane-v1.json | 132 | Manifest Write Failure Ratio |
| bioetl-control-plane-v1.json | 133 | Ledger Append Failure Ratio |
| bioetl-control-plane-v1.json | 134 | Replay Drift by Type |
| bioetl-control-plane-v1.json | 135 | Replay Lag Trend |
| bioetl-control-plane-v1.json | 136 | GLOBAL Control-Plane Read Failure Ratio |
| bioetl-control-plane-v1.json | 137 | Lineage Fragment Persistence Failures |
| bioetl-control-plane-v1.json | 138 | Lineage Refs Missing by Layer / Ref Type |
| bioetl-control-plane-v1.json | 139 | Known Missing Replay-Safety Signals |
| bioetl-control-plane-v1.json | 891 | Replay Safety State |
| bioetl-control-plane-v1.json | 892 | Checkpoint Freshness (hours since last op) |
| bioetl-control-plane-v1.json | 893 | Ledger / Manifest Consistency |
| bioetl-control-plane-v1.json | 894 | Known Blind Spots |
| bioetl-dq-v2.json | 1 | Data Flow in Range: Bronze -> Silver -> Gold |
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
| bioetl-dq-v2.json | 101 | Latest Successful Data Timestamp |
| bioetl-dq-v2.json | 116 | Lineage Refs Missing |
| bioetl-dq-v2.json | 117 | Silver Filter Rejects |
| bioetl-dq-v2.json | 118 | Silver Filter Rejects by Pipeline |
| bioetl-dq-v2.json | 121 | Top Silver Reject Reasons (Pareto) |
| bioetl-dq-v2.json | 122 | Top Silver Reject Fields |
| bioetl-dq-v2.json | 150 | Control-plane aggregates note |
| bioetl-dq-v2.json | 151 | Gold Strict Validation Failures |
| bioetl-dq-v2.json | 152 | Silver Filter Reject Accounting Mismatch |
| bioetl-dq-v2.json | 153 | Data Quality Score Trend (Volume-weighted) |
| bioetl-dq-v2.json | 154 | DQ Impact on Deliverability (Blocked Share) |
| bioetl-dq-v2.json | 155 | DQ Impact on Deliverability Trend (Blocked Share %) |
| bioetl-overview-v2.json | 99 | L0 Overview Scope |
| bioetl-overview-v2.json | 214 | System Status |
| bioetl-overview-v2.json | 215 | Next Action |
| bioetl-overview-v2.json | 9002 | L0 Inputs |
| bioetl-overview-v2.json | 9003 | Runtime Blockers Current |
| bioetl-overview-v2.json | 9004 | DQ Status Current |
| bioetl-overview-v2.json | 9005 | Gold Lifecycle Current |
| bioetl-overview-v2.json | 9006 | Control Plane Current |
| bioetl-overview-v2.json | 9007 | Provider GLOBAL Scope |
| bioetl-overview-v2.json | 9008 | Workflow Selected Scope |
| bioetl-overview-v2.json | 9009 | Range Evidence (Historical / Recent History) |
| bioetl-overview-v2.json | 9010 | Historical Failures (range evidence) |
| bioetl-overview-v2.json | 9011 | Recent terminal runs (range evidence) |
| bioetl-overview-v2.json | 9012 | Diagnostics & Docs (Logs / Traces / Raw Metrics) |
| bioetl-overview-v2.json | 9013 | Workflow GLOBAL Scope |
| bioetl-overview-v2.json | 9014 | Diagnostics Navigation |
| bioetl-provider-health-v2.json | 1 | Monitor Health Check Latency by Provider (p95) |
| bioetl-provider-health-v2.json | 2 | Monitor Healthy Checks |
| bioetl-provider-health-v2.json | 7 | Track Health Checks Total |
| bioetl-provider-health-v2.json | 31 | Monitor Circuit Breaker State (max) |
| bioetl-provider-health-v2.json | 32 | Track Circuit Breaker Trips by Provider |
| bioetl-provider-health-v2.json | 102 | Inspect Provider Health Check Latency (p95) - $provider |
| bioetl-provider-health-v2.json | 104 | Track Provider Failure Rate |
| bioetl-provider-health-v2.json | 105 | Track Degraded Checks |
| bioetl-provider-health-v2.json | 106 | Track Failure and Degraded Trend by Provider |
| bioetl-provider-health-v2.json | 107 | Track Provider Failure Share (Selected Range) |
| bioetl-provider-health-v2.json | 108 | Track Retries Exhausted by Provider/Operation |
| bioetl-provider-health-v2.json | 109 | Track Retries Exhausted Trend by Provider/Operation |
| bioetl-provider-health-v2.json | 110 | Inspect Adapter Request Latency by Endpoint (p95) |
| bioetl-provider-health-v2.json | 111 | Inspect HTTP Errors by Method/Error Type |
| bioetl-provider-health-v2.json | 112 | Track Rate Limiter Wait by Provider (p95) |
| bioetl-provider-health-v2.json | 113 | Monitor Minimum Rate Limiter Tokens Available |
| bioetl-provider-health-v2.json | 114 | Monitor Current Provider Health Status |
| bioetl-runtime.json | 1 | Runtime Scope |
| bioetl-runtime.json | 4 | DQ Alert Conditions |
| bioetl-runtime.json | 5 | Control-plane Alert Conditions |
| bioetl-runtime.json | 6 | GLOBAL Provider Alert Conditions |
| bioetl-runtime.json | 7 | Freshness Alert Conditions |
| bioetl-runtime.json | 16 | Runtime Blockers / 15m |
| bioetl-runtime.json | 21 | Memory Pressure Active / 15m |
| bioetl-runtime.json | 205 | Failed Runs / 15m |
| bioetl-runtime.json | 207 | Pipeline Phase Duration p50/p95/p99 |
| bioetl-runtime.json | 209 | Shutdown Initiated by Reason / Interval |
| bioetl-runtime.json | 210 | Shutdown Completed by Reason / Interval |
| bioetl-runtime.json | 220 | Runtime Error Rate / 30m |
| bioetl-runtime.json | 221 | Errors by Stage / Error Code / Range |
| bioetl-runtime.json | 222 | Incident Summary |
| bioetl-runtime.json | 230 | Pipeline Alert Conditions |
| bioetl-runtime.json | 236 | No-Records Runs / 30m |
| bioetl-runtime.json | 237 | Worst Stage Lag / 15m |
| bioetl-runtime.json | 238 | Stage Backlog Trend |
| bioetl-runtime.json | 239 | Pipeline Duration p50/p95/p99 |
| bioetl-runtime.json | 240 | Records by Stage / Interval |
| bioetl-runtime.json | 241 | Records by Stage / Run Type / Range |
| bioetl-runtime.json | 242 | Active Runtime Blocker Detail |
| bioetl-runtime.json | 243 | Stage Expectedness |
| bioetl-runtime.json | 9991 | Recommended Next Drilldown |
| bioetl-silver-reject-explorer.json | 1 | Inspect Explorer Scope |
| bioetl-silver-reject-explorer.json | 2 | Monitor Filtered Records Total |
| bioetl-silver-reject-explorer.json | 3 | Track Reject Rate vs Bronze |
| bioetl-silver-reject-explorer.json | 4 | Inspect Run Scope Summary |
| bioetl-silver-reject-explorer.json | 5 | Inspect Top Reject Reasons |
| bioetl-silver-reject-explorer.json | 6 | Inspect Top Reject Fields |
| bioetl-silver-reject-explorer.json | 7 | Inspect Top Reason Signatures |
| bioetl-silver-reject-explorer.json | 8 | Inspect Filtered Records Table |
| bioetl-silver-reject-explorer.json | 9 | Inspect Selected Record Details |
| bioetl-workflow-overview.json | 1 | Monitor Workflow Scope |
| bioetl-workflow-overview.json | 2 | Monitor Workflow Runs |
| bioetl-workflow-overview.json | 3 | Inspect Failed Workflow Runs |
| bioetl-workflow-overview.json | 4 | Track Step Outcomes by Kind |
| bioetl-workflow-overview.json | 5 | Track Step Duration p95 |
