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
| bioetl-control-plane-v1.json | 1000 | Navigate Dashboards |
| bioetl-control-plane-v1.json | 9400 | Inspect Scope & Evidence |
| bioetl-control-plane-v1.json | 9401 | Monitor Replay Readiness |
| bioetl-control-plane-v1.json | 9418 | Review Selected-Run Trust |
| bioetl-control-plane-v1.json | 9416 | Review Retention Compliance |
| bioetl-control-plane-v1.json | 891 | Monitor Replay Safety |
| bioetl-control-plane-v1.json | 892 | Monitor Checkpoint Age |
| bioetl-control-plane-v1.json | 893 | Monitor Manifest/Ledger |
| bioetl-control-plane-v1.json | 907 | Monitor Telemetry |
| bioetl-control-plane-v1.json | 9419 | Review Lineage Validation |
| bioetl-control-plane-v1.json | 906 | Review Recovery Action |
| bioetl-control-plane-v1.json | 9415 | Review Lineage Validation |
| bioetl-control-plane-v1.json | 902 | Inspect Replay & Checkpoint Evidence |
| bioetl-control-plane-v1.json | 894 | Review Coverage Limits |
| bioetl-control-plane-v1.json | 130 | Track Replay Blockers |
| bioetl-control-plane-v1.json | 3 | Track Checkpoint Incompatibilities |
| bioetl-control-plane-v1.json | 104 | Track Unreconstructable Replays |
| bioetl-control-plane-v1.json | 120 | Track Replay Drift |
| bioetl-control-plane-v1.json | 101 | Track Checkpoint Load Failures |
| bioetl-control-plane-v1.json | 102 | Track Checkpoint Save Failures |
| bioetl-control-plane-v1.json | 103 | Track Global Checkpoint Admin Failures |
| bioetl-control-plane-v1.json | 121 | Track Peak Replay Lag |
| bioetl-control-plane-v1.json | 5 | Compare Checkpoint Outcomes |
| bioetl-control-plane-v1.json | 134 | Track Replay Drift by Type |
| bioetl-control-plane-v1.json | 135 | Track Replay Lag |
| bioetl-control-plane-v1.json | 105 | Track Checkpoint Save Latency |
| bioetl-control-plane-v1.json | 106 | Track Global Checkpoint Admin Latency |
| bioetl-control-plane-v1.json | 9413 | Review Checkpoint Validation |
| bioetl-control-plane-v1.json | 901 | Inspect Manifest & Ledger Evidence |
| bioetl-control-plane-v1.json | 908 | Review Terminal Run Outcomes |
| bioetl-control-plane-v1.json | 2 | Track Ledger Append Failures |
| bioetl-control-plane-v1.json | 1 | Track Manifest Write Failures |
| bioetl-control-plane-v1.json | 131 | Compare Manifest Writes by Status |
| bioetl-control-plane-v1.json | 7 | Compare Ledger Appends by Type & Status |
| bioetl-control-plane-v1.json | 132 | Monitor Manifest Failures (30m) |
| bioetl-control-plane-v1.json | 133 | Monitor Ledger Failures (30m) |
| bioetl-control-plane-v1.json | 9414 | Review Manifest Validation |
| bioetl-control-plane-v1.json | 903 | Inspect Global Store Reliability |
| bioetl-control-plane-v1.json | 4 | Track Global Read Failures |
| bioetl-control-plane-v1.json | 136 | Monitor Global Read Failures (30m) |
| bioetl-control-plane-v1.json | 6 | Compare Global Reads by Store |
| bioetl-control-plane-v1.json | 111 | Track Global Read Latency |
| bioetl-control-plane-v1.json | 904 | Inspect Audit & Lineage Evidence |
| bioetl-control-plane-v1.json | 122 | Track Missing Lineage References |
| bioetl-control-plane-v1.json | 137 | Track Lineage Persistence Failures |
| bioetl-control-plane-v1.json | 138 | Review Missing Lineage by Layer |
| bioetl-control-plane-v1.json | 107 | Compare Global Audit Write Outcomes |
| bioetl-control-plane-v1.json | 108 | Compare Global Audit Query Outcomes |
| bioetl-control-plane-v1.json | 109 | Track Global Audit Write Latency |
| bioetl-control-plane-v1.json | 110 | Track Global Audit Query Latency |
| bioetl-control-plane-v1.json | 112 | Compare Lineage Persistence Outcomes |
| bioetl-control-plane-v1.json | 905 | Inspect Run Identity Evidence |
| bioetl-control-plane-v1.json | 9404 | Review Identity Anchors |
| bioetl-control-plane-v1.json | 9407 | Inspect Identity Values |
| bioetl-control-plane-v1.json | 9410 | Explain Missing Identity Data |
| bioetl-control-plane-v1.json | 9411 | Explain Missing Record Counts |
| bioetl-control-plane-v1.json | 9405 | Review Identity Gaps |
| bioetl-control-plane-v1.json | 9406 | Compare Checkpoint Anchors |
| bioetl-control-plane-v1.json | 9408 | Review Required Replay Anchors |
| bioetl-control-plane-v1.json | 9409 | Review Additional Forensic Anchors |
| bioetl-control-plane-v1.json | 139 | Review Uncovered Replay Signals |
| bioetl-control-plane-v1.json | 9412 | Inspect Run Details |
| bioetl-control-plane-v1.json | 9402 | Review Run Summary |
| bioetl-control-plane-v1.json | 9403 | Review Processed Records |
| bioetl-control-plane-v1.json | 9417 | Review Bounded Failure Reasons |
| bioetl-dq-v2.json | 1000 | Navigate Dashboards |
| bioetl-dq-v2.json | 9400 | Understand Evidence Scope |
| bioetl-dq-v2.json | 9401 | Monitor Current DQ Status |
| bioetl-dq-v2.json | 9103 | Start DQ Triage |
| bioetl-dq-v2.json | 9101 | Monitor DQ Threshold State |
| bioetl-dq-v2.json | 9405 | Selected Run · Identity & Accounting |
| bioetl-dq-v2.json | 9402 | Inspect Run Identity |
| bioetl-dq-v2.json | 9403 | Inspect Processed Records |
| bioetl-dq-v2.json | 9406 | Review Selected Run Summary |
| bioetl-dq-v2.json | 9404 | Selected Range · Impact & Freshness |
| bioetl-dq-v2.json | 9102 | Inspect Current DQ Reasons |
| bioetl-dq-v2.json | 2 | Monitor Volume-Weighted DQ Score |
| bioetl-dq-v2.json | 5 | Monitor Worst-Entity DQ Score |
| bioetl-dq-v2.json | 8 | Monitor Worst Freshness Age |
| bioetl-dq-v2.json | 154 | Monitor Blocked Records |
| bioetl-dq-v2.json | 6 | Monitor Quarantined Records |
| bioetl-dq-v2.json | 117 | Monitor Silver Filter Rejects |
| bioetl-dq-v2.json | 220 | Selected Range · Reject Evidence |
| bioetl-dq-v2.json | 152 | Monitor Silver Reject Mismatch |
| bioetl-dq-v2.json | 121 | Inspect Top Silver Reject Reasons |
| bioetl-dq-v2.json | 122 | Inspect Top Silver Reject Fields |
| bioetl-dq-v2.json | 118 | Inspect Silver Rejects by Pipeline |
| bioetl-dq-v2.json | 156 | Inspect Gold Reject Outcomes by Pipeline |
| bioetl-dq-v2.json | 221 | Selected Range · Validation Diagnostics |
| bioetl-dq-v2.json | 1 | Track Record Flow by Stage |
| bioetl-dq-v2.json | 3 | Monitor Bronze Records |
| bioetl-dq-v2.json | 4 | Monitor Gold Records |
| bioetl-dq-v2.json | 101 | Inspect Latest Successful Data |
| bioetl-dq-v2.json | 9 | Inspect Quarantine Error Types |
| bioetl-dq-v2.json | 12 | Monitor Silver Validation Failures |
| bioetl-dq-v2.json | 151 | Monitor Gold Validation Failures |
| bioetl-dq-v2.json | 10 | Track DQ Anomalies |
| bioetl-dq-v2.json | 11 | Track DQ Check Duration p95 |
| bioetl-dq-v2.json | 155 | Track DQ Threshold Events |
| bioetl-dq-v2.json | 153 | Track Volume-Weighted DQ Score |
| bioetl-dq-v2.json | 116 | Inspect Lineage in Control Plane |
| bioetl-dq-v2.json | 150 | Inspect Aggregate Control-Plane Issues |
| bioetl-incident-v1.json | 1000 | Navigate Dashboards |
| bioetl-incident-v1.json | 9400 | Understand Incident Scope |
| bioetl-incident-v1.json | 9401 | Monitor Incident Status |
| bioetl-incident-v1.json | 2001 | Start Incident Triage |
| bioetl-incident-v1.json | 2010 | Inspect Ranked Suspects |
| bioetl-incident-v1.json | 2020 | Review Alert Evidence |
| bioetl-incident-v1.json | 2005 | Monitor Current Alerts |
| bioetl-incident-v1.json | 2006 | Track Alert State History |
| bioetl-incident-v1.json | 2007 | Assess Impact & Confidence |
| bioetl-incident-v1.json | 2099 | Domain Suspect Details |
| bioetl-incident-v1.json | 2002 | Inspect Runtime Suspects |
| bioetl-incident-v1.json | 2003 | Inspect Provider Suspects |
| bioetl-incident-v1.json | 2004 | Inspect DQ Suspects |
| bioetl-incident-v1.json | 2100 | Inspect Selected Run Summary |
| bioetl-incident-v1.json | 2101 | Review Selected Run Summary |
| bioetl-overview-v2.json | 1000 | Navigate Dashboards |
| bioetl-overview-v2.json | 99 | Inspect Scope & Evidence |
| bioetl-overview-v2.json | 9603 | Review Selected Run Summary |
| bioetl-overview-v2.json | 214 | Monitor Fleet Health |
| bioetl-overview-v2.json | 215 | Review First Action |
| bioetl-overview-v2.json | 9002 | Review Domain Status |
| bioetl-overview-v2.json | 9600 | Inspect Alerts |
| bioetl-overview-v2.json | 9601 | Review Active Alerts |
| bioetl-overview-v2.json | 9030 | Domain Status Tracks |
| bioetl-overview-v2.json | 9031 | Review All Domain Status |
| bioetl-overview-v2.json | 9018 | Track Runtime Blockers |
| bioetl-overview-v2.json | 9019 | Track Data Quality Status |
| bioetl-overview-v2.json | 9020 | Track Gold Lifecycle |
| bioetl-overview-v2.json | 9009 | Inspect Range Evidence |
| bioetl-overview-v2.json | 9010 | Review Failed Runs |
| bioetl-overview-v2.json | 9011 | Review Recent Non-success Terminal Runs |
| bioetl-overview-v2.json | 9015 | Track Silver Rejects |
| bioetl-overview-v2.json | 9012 | Inspect Domain Diagnostics |
| bioetl-overview-v2.json | 9006 | Review Control Plane Status |
| bioetl-overview-v2.json | 9003 | Review Runtime Status |
| bioetl-overview-v2.json | 9004 | Review Data Quality Status |
| bioetl-overview-v2.json | 9007 | Review Global Provider Status |
| bioetl-overview-v2.json | 9005 | Review Data Validation Status |
| bioetl-overview-v2.json | 9013 | Review Workflow Status |
| bioetl-overview-v2.json | 9021 | Navigate Diagnostics |
| bioetl-overview-v2.json | 9602 | Inspect Run Context |
| bioetl-overview-v2.json | 9300 | Review Run Identity |
| bioetl-overview-v2.json | 9301 | Review Processed Records |
| bioetl-provider-health-v2.json | 1000 | Navigate Dashboards |
| bioetl-provider-health-v2.json | 9400 | Understand Evidence Scope |
| bioetl-provider-health-v2.json | 9401 | Monitor Selected Provider |
| bioetl-provider-health-v2.json | 9002 | Start Provider Triage |
| bioetl-provider-health-v2.json | 9101 | Monitor Fleet Severity |
| bioetl-provider-health-v2.json | 9107 | Inspect Status Reason |
| bioetl-provider-health-v2.json | 9104 | Monitor Telemetry Presence |
| bioetl-provider-health-v2.json | 9106 | Inspect Fleet Non-OK and Causes |
| bioetl-provider-health-v2.json | 9102 | Inspect Non-OK Providers |
| bioetl-provider-health-v2.json | 9103 | Inspect Top Provider Causes |
| bioetl-provider-health-v2.json | 9105 | Inspect Full Fleet Evidence |
| bioetl-provider-health-v2.json | 9111 | Inspect Full Fleet Severity |
| bioetl-provider-health-v2.json | 9112 | Inspect Full Non-OK Providers |
| bioetl-provider-health-v2.json | 9113 | Inspect Full Provider Causes |
| bioetl-provider-health-v2.json | 91 | Selected Provider Details |
| bioetl-provider-health-v2.json | 106 | Track Health Failures & Degradation |
| bioetl-provider-health-v2.json | 107 | Track Failure Share |
| bioetl-provider-health-v2.json | 108 | Inspect Exhausted Retries |
| bioetl-provider-health-v2.json | 109 | Track Exhausted Retries |
| bioetl-provider-health-v2.json | 102 | Inspect Health-Check Latency p95 |
| bioetl-provider-health-v2.json | 110 | Track Request Latency p95 |
| bioetl-provider-health-v2.json | 111 | Track Rate-Limit Errors |
| bioetl-provider-health-v2.json | 115 | Track Network & Timeout Errors |
| bioetl-provider-health-v2.json | 112 | Track Rate-Limiter Wait p95 |
| bioetl-provider-health-v2.json | 113 | Monitor Available Rate-Limit Tokens |
| bioetl-provider-health-v2.json | 31 | Monitor Circuit-Breaker State |
| bioetl-provider-health-v2.json | 32 | Track Circuit-Breaker Trips |
| bioetl-provider-health-v2.json | 9404 | Range & Debug Evidence |
| bioetl-provider-health-v2.json | 114 | Inspect Raw Health Status |
| bioetl-provider-health-v2.json | 1 | Track Health-Check Latency p95 |
| bioetl-provider-health-v2.json | 2 | Monitor Healthy Checks |
| bioetl-provider-health-v2.json | 105 | Monitor Degraded Checks |
| bioetl-provider-health-v2.json | 104 | Track Failure Rate |
| bioetl-provider-health-v2.json | 7 | Monitor Health Checks |
| bioetl-provider-health-v2.json | 9405 | Run Context |
| bioetl-provider-health-v2.json | 9402 | Inspect Run Identity |
| bioetl-provider-health-v2.json | 9403 | Inspect Processed Records |
| bioetl-run-explorer-v1.json | 1000 | Navigate Dashboards |
| bioetl-run-explorer-v1.json | 1 | Understand Run Scope |
| bioetl-run-explorer-v1.json | 3010 | Inspect Recent Runs (last 4) |
| bioetl-run-explorer-v1.json | 9402 | Inspect Run Identity |
| bioetl-run-explorer-v1.json | 3099 | Selected Run Details |
| bioetl-run-explorer-v1.json | 3021 | Inspect Recent Runs (last 20) |
| bioetl-run-explorer-v1.json | 3022 | Inspect Full Run Identity |
| bioetl-run-explorer-v1.json | 3023 | Inspect Full Processed Records |
| bioetl-run-explorer-v1.json | 3011 | Inspect Stage Funnel |
| bioetl-run-explorer-v1.json | 3012 | Inspect Top Run Reasons |
| bioetl-run-explorer-v1.json | 3015 | Inspect Reconciliation |
| bioetl-run-explorer-v1.json | 3016 | Inspect Layer Accounting |
| bioetl-run-explorer-v1.json | 3013 | Inspect Run Artifacts |
| bioetl-run-explorer-v1.json | 3014 | Inspect Timings & Failure |
| bioetl-run-explorer-v1.json | 3001 | Continue Run Investigation |
| bioetl-run-explorer-v1.json | 3098 | Browse Workflow Runs |
| bioetl-run-explorer-v1.json | 3020 | Inspect Recent Workflow Runs (last 20) |
| bioetl-runtime.json | 1000 | Navigate Dashboards |
| bioetl-runtime.json | 9400 | Understand Pipeline Scope |
| bioetl-runtime.json | 9401 | Monitor Pipeline Status |
| bioetl-runtime.json | 9991 | Start Pipeline Triage |
| bioetl-runtime.json | 9101 | Review Runtime Blockers |
| bioetl-runtime.json | 9102 | Monitor Metrics Coverage |
| bioetl-runtime.json | 252 | Inspect Detection Signals |
| bioetl-runtime.json | 238 | Track Stage Backlog Trend |
| bioetl-runtime.json | 240 | Track Records by Stage / Interval |
| bioetl-runtime.json | 242 | Inspect Active Runtime Blocker Detail |
| bioetl-runtime.json | 9105 | Track Stage Lag |
| bioetl-runtime.json | 243 | Inspect Stage Expectedness |
| bioetl-runtime.json | 220 | Monitor Runtime Error Rate |
| bioetl-runtime.json | 253 | Localize Runtime Cause |
| bioetl-runtime.json | 207 | Track Phase Duration |
| bioetl-runtime.json | 239 | Track Pipeline Duration |
| bioetl-runtime.json | 256 | Review Errors by Stage & Code |
| bioetl-runtime.json | 241 | Compare Records by Stage & Run Type |
| bioetl-runtime.json | 254 | Review Escalation Paths |
| bioetl-runtime.json | 2541 | Review Runtime Escalation |
| bioetl-runtime.json | 230 | Monitor Pipeline Alert Conditions |
| bioetl-runtime.json | 236 | Monitor No-Records Runs |
| bioetl-runtime.json | 21 | Monitor Memory Pressure Active |
| bioetl-runtime.json | 2542 | Review Cross-Domain Handoffs |
| bioetl-runtime.json | 4 | Inspect DQ Alert Conditions |
| bioetl-runtime.json | 5 | Inspect Control Plane Alert Conditions |
| bioetl-runtime.json | 6 | Inspect Provider Alert Conditions |
| bioetl-runtime.json | 259 | Inspect Global Provider Alert Conditions |
| bioetl-runtime.json | 7 | Inspect Entities Stale Over 24h |
| bioetl-runtime.json | 2543 | Review Global Process Signals |
| bioetl-runtime.json | 209 | Track Global Shutdown Starts |
| bioetl-runtime.json | 210 | Track Global Shutdown Completions |
| bioetl-runtime.json | 9992 | Inspect Secondary Runtime Indicators |
| bioetl-runtime.json | 237 | Monitor Worst Stage Lag |
| bioetl-runtime.json | 16 | Monitor Runtime Blockers |
| bioetl-runtime.json | 205 | Monitor Failed Runs |
| bioetl-runtime.json | 9993 | Inspect Run Context |
| bioetl-runtime.json | 9402 | Inspect Pipeline Identity |
| bioetl-runtime.json | 9403 | Inspect Processed Records |
| bioetl-runtime.json | 9998 | Review Selected Run Summary |
| bioetl-runtime.json | 9994 | Inspect Workflow Evidence |
| bioetl-runtime.json | 9996 | Track Failed Workflow Runs |
| bioetl-runtime.json | 9997 | Track Failed Workflow Steps |
