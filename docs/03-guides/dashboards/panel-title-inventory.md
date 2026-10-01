# Panel Title Inventory

Generated from `grafana/dashboards/*.json`.

## KPI ownership contract anchors

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (`kpi_ownership`).

| KPI key | Canonical UID | Mirror panel(s) |
|---|---|---|
| `failed_runs_in_range` | `bioetl-overview-v2` | — (dashboard retired) |
| `worst_lag_stage` | `bioetl-overview-v2` | — (dashboard retired) |
| `worst_backlog_stage` | `bioetl-overview-v2` | — (dashboard retired) |

| Dashboard | Panel ID | Title |
| --- | ---: | --- |
| bioetl-control-plane-v1.json | 1000 | Navigate Dashboards |
| bioetl-control-plane-v1.json | 9400 | Inspect Scope & Evidence |
| bioetl-control-plane-v1.json | 9418 | Review Selected-Run Trust |
| bioetl-control-plane-v1.json | 9416 | Review Retention Compliance |
| bioetl-control-plane-v1.json | 9419 | Review Lineage Validation |
| bioetl-control-plane-v1.json | 9415 | Review Lineage Validation |
| bioetl-control-plane-v1.json | 902 | Inspect Checkpoint and Replay Checks |
| bioetl-control-plane-v1.json | 9413 | Review Checkpoint Validation |
| bioetl-control-plane-v1.json | 9423 | Review Exact Replay Checks |
| bioetl-control-plane-v1.json | 901 | Inspect Manifest Validation |
| bioetl-control-plane-v1.json | 9414 | Review Manifest Validation |
| bioetl-control-plane-v1.json | 905 | Inspect Run Identity Evidence |
| bioetl-control-plane-v1.json | 9407 | Inspect Identity Values |
| bioetl-control-plane-v1.json | 9410 | Explain Missing Identity Data |
| bioetl-control-plane-v1.json | 9411 | Explain Missing Record Counts |
| bioetl-control-plane-v1.json | 9405 | Review Identity Gaps |
| bioetl-control-plane-v1.json | 9408 | Review Required Replay Anchors |
| bioetl-control-plane-v1.json | 9406 | Compare Checkpoint Anchors |
| bioetl-control-plane-v1.json | 9409 | Review Additional Forensic Anchors |
| bioetl-control-plane-v1.json | 139 | Review Uncovered Replay Signals |
| bioetl-control-plane-v1.json | 9412 | Inspect Run Details |
| bioetl-control-plane-v1.json | 9402 | Review Run Summary |
| bioetl-control-plane-v1.json | 9417 | Review Bounded Failure Reasons |
| bioetl-control-plane-v1.json | 9422 | Review Exact Replay Readiness |
| bioetl-control-plane-v1.json | 9420 | Inspect Complete Run Discovery |
| bioetl-control-plane-v1.json | 9421 | Inspect Latest Complete Run |
| bioetl-dq-v2.json | 1000 | Navigate Dashboards |
| bioetl-dq-v2.json | 9400 | Understand Evidence Scope |
| bioetl-dq-v2.json | 9406 | Review Selected Run Status |
| bioetl-dq-v2.json | 9402 | Inspect Run Identity |
| bioetl-dq-v2.json | 9403 | Inspect Processed Records |
| bioetl-dq-v2.json | 9450 | Inspect Saved Run Evidence |
| bioetl-dq-v2.json | 9460 | Inspect Selected Run Stages |
| bioetl-dq-v2.json | 9451 | Inspect Selected Run Domains |
| bioetl-dq-v2.json | 9452 | Inspect Selected Run Identity |
| bioetl-incident-v1.json | 1000 | Navigate Dashboards |
| bioetl-incident-v1.json | 9400 | Understand Incident Scope |
| bioetl-incident-v1.json | 9401 | Monitor Scope Status |
| bioetl-incident-v1.json | 2001 | Start Incident Triage |
| bioetl-incident-v1.json | 2010 | Inspect Ranked Suspects |
| bioetl-incident-v1.json | 2005 | Monitor Global Alerts |
| bioetl-incident-v1.json | 2020 | Review Alert Evidence |
| bioetl-incident-v1.json | 2006 | Track Alert State History |
| bioetl-incident-v1.json | 2007 | Assess Impact & Confidence |
| bioetl-incident-v1.json | 2099 | Domain Suspect Details · GLOBAL / CURRENT |
| bioetl-incident-v1.json | 2002 | Inspect Runtime Suspects |
| bioetl-incident-v1.json | 2003 | Inspect Provider Suspects |
| bioetl-incident-v1.json | 2004 | Inspect DQ Suspects |
| bioetl-incident-v1.json | 22011 | Inspect Global Signal Measurements |
| bioetl-incident-v1.json | 2100 | Inspect Selected Run Summary |
| bioetl-incident-v1.json | 2101 | Review Selected Run Status |
| bioetl-incident-v1.json | 8808 | Pipeline fleet and range, not this Run ID |
| bioetl-incident-v1.json | 18940 | Monitor Pipeline Status |
| bioetl-incident-v1.json | 9101 | Review Runtime Blockers |
| bioetl-incident-v1.json | 9102 | Monitor Coverage |
| bioetl-incident-v1.json | 2460 | Review Stage Progress |
| bioetl-incident-v1.json | 9463 | Review Total Run Duration |
| bioetl-incident-v1.json | 238 | Track Stage Backlog Trend |
| bioetl-incident-v1.json | 207 | Track Phase Duration |
| bioetl-incident-v1.json | 239 | Track Pipeline Duration |
| bioetl-incident-v1.json | 2541 | Review Runtime Escalation |
| bioetl-incident-v1.json | 237 | Monitor Worst Stage Lag |
| bioetl-incident-v1.json | 16 | Monitor Active Blocker Count |
| bioetl-incident-v1.json | 205 | Monitor Failed Runs |
| bioetl-incident-v1.json | 230 | Monitor Pipeline Alerts |
| bioetl-incident-v1.json | 9996 | Track Failed Workflow Runs |
| bioetl-incident-v1.json | 236 | Monitor No-Records Runs |
| bioetl-incident-v1.json | 9997 | Track Failed Workflow Steps |
| bioetl-incident-v1.json | 21 | Monitor Memory Pressure |
| bioetl-incident-v1.json | 256 | Review Errors by Stage & Code |
| bioetl-incident-v1.json | 241 | Compare Records by Stage & Run Type |
| bioetl-incident-v1.json | 891 | Monitor Replay |
| bioetl-incident-v1.json | 892 | Track Checkpoint |
| bioetl-incident-v1.json | 893 | Monitor Ledger |
| bioetl-incident-v1.json | 907 | Monitor Telemetry |
| bioetl-incident-v1.json | 2542 | Review Cross-Domain Handoffs |
| bioetl-incident-v1.json | 240 | Track Records by Stage / Interval |
| bioetl-incident-v1.json | 4 | Inspect DQ Alert Conditions |
| bioetl-incident-v1.json | 5 | Inspect Control Plane Alerts |
| bioetl-incident-v1.json | 6 | Inspect Provider Alerts |
| bioetl-incident-v1.json | 9991 | Start Pipeline Triage |
| bioetl-incident-v1.json | 894 | Review Coverage Limits |
| bioetl-incident-v1.json | 259 | Inspect Global Provider Alert Conditions |
| bioetl-incident-v1.json | 908 | Review Observed Terminal Counters |
| bioetl-incident-v1.json | 7 | Inspect Entities Stale Over 24h |
| bioetl-incident-v1.json | 8804 | Track Global Read Failures |
| bioetl-incident-v1.json | 136 | Monitor Global Read Failures (30m) |
| bioetl-incident-v1.json | 122 | Track Missing Lineage |
| bioetl-incident-v1.json | 137 | Track Lineage Failures |
| bioetl-incident-v1.json | 2 | Track Ledger Failures |
| bioetl-incident-v1.json | 130 | Track Replay Blockers |
| bioetl-incident-v1.json | 242 | Inspect Active Runtime Blocker Detail |
| bioetl-incident-v1.json | 2461 | Inspect Current Missing Stage Signals |
| bioetl-incident-v1.json | 2543 | Review Global Process Signals |
| bioetl-incident-v1.json | 8806 | Compare Global Reads by Store |
| bioetl-incident-v1.json | 1 | Track Manifest Failures |
| bioetl-incident-v1.json | 3 | Track Incompatibilities |
| bioetl-incident-v1.json | 104 | Track Unreconstructable |
| bioetl-incident-v1.json | 138 | Review Missing Lineage by Layer |
| bioetl-incident-v1.json | 120 | Track Replay Drift |
| bioetl-incident-v1.json | 132 | Monitor Manifest (30m) |
| bioetl-incident-v1.json | 209 | Track Global Shutdown Starts |
| bioetl-incident-v1.json | 101 | Track Load Failures |
| bioetl-incident-v1.json | 133 | Monitor Ledger (30m) |
| bioetl-incident-v1.json | 210 | Track Global Shutdown Completions |
| bioetl-incident-v1.json | 102 | Track Save Failures |
| bioetl-incident-v1.json | 9491 | Inspect Telemetry Coverage |
| bioetl-incident-v1.json | 103 | Track Global Admin Failures |
| bioetl-incident-v1.json | 111 | Track Global Read Latency |
| bioetl-incident-v1.json | 131 | Track Observed Manifest Write Increments |
| bioetl-incident-v1.json | 121 | Track Peak Replay Lag |
| bioetl-incident-v1.json | 107 | Compare Global Audit Write Outcomes |
| bioetl-incident-v1.json | 134 | Track Replay Drift by Type |
| bioetl-incident-v1.json | 9105 | Track Stage Lag |
| bioetl-incident-v1.json | 8805 | Compare Checkpoint Outcomes |
| bioetl-incident-v1.json | 108 | Compare Global Audit Query Outcomes |
| bioetl-incident-v1.json | 135 | Track Replay Lag |
| bioetl-incident-v1.json | 8807 | Compare Ledger Appends by Type & Status |
| bioetl-incident-v1.json | 243 | Inspect Stage Expectedness |
| bioetl-incident-v1.json | 105 | Track Checkpoint Save Latency |
| bioetl-incident-v1.json | 109 | Track Global Audit Write Latency |
| bioetl-incident-v1.json | 106 | Track Global Checkpoint Admin Latency |
| bioetl-incident-v1.json | 110 | Track Global Audit Query Latency |
| bioetl-incident-v1.json | 220 | Monitor Runtime Error Rate |
| bioetl-incident-v1.json | 112 | Compare Lineage Persistence Outcomes |
| bioetl-incident-v1.json | 32010 | Browse Global Suspects |
| bioetl-incident-v1.json | 22010 | Inspect Global Suspects (Full) |
| bioetl-incident-v1.json | 32005 | Browse Global Alerts |
| bioetl-incident-v1.json | 22005 | Monitor Global Alerts (Full) |
| bioetl-incident-v1.json | 9450 | Inspect Saved Run Evidence |
| bioetl-incident-v1.json | 9460 | Inspect Selected Run Stages |
| bioetl-incident-v1.json | 9451 | Inspect Selected Run Domains |
| bioetl-incident-v1.json | 9452 | Inspect Selected Run Identity |
| bioetl-incident-v1.json | 9700 | Inspect Current Workflow Evidence |
| bioetl-incident-v1.json | 9701 | Review Current Workflow Evidence |
| bioetl-overview-v2.json | 1000 | Navigate Dashboards |
| bioetl-overview-v2.json | 99 | Inspect Scope & Evidence |
| bioetl-overview-v2.json | 9604 | Overall Verdict |
| bioetl-overview-v2.json | 9002 | Run Domains |
| bioetl-overview-v2.json | 9603 | Selected Run Status |
| bioetl-overview-v2.json | 9300 | Run Identity |
| bioetl-overview-v2.json | 9480 | Provider Evidence |
| bioetl-overview-v2.json | 9481 | Provider Check |
| bioetl-overview-v2.json | 9460 | Inspect Selected Run Stages |
| bioetl-overview-v2.json | 9482 | Data Quality |
| bioetl-run-explorer-v1.json | 1 | Understand Run Scope |
| bioetl-run-explorer-v1.json | 3010 | Inspect Recent Runs (last 10) |
