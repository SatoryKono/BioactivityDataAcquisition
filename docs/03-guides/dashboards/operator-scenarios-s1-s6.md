# Operator scenarios S1–S6 (Grafana simplification #6570 / #6577)

Offline-first playbook for the post-simplification dashboard set. **Family cause**
(which surface / which KPI) is the acceptance bar; row-level forensics stay on CLI.

## Shipped surfaces (interim 5, target 4)

| Surface | UID | Role |
| --- | --- | --- |
| **Trust** | `bioetl-control-plane-v1` | Replay / resume safety |
| **Overview** | `bioetl-overview-v2` | L0 system state + first action + alerts triage (collapsed) |
| **Pipeline Diagnostics** | `bioetl-runtime` | Execution blockers / error rate / workflow band |
| **Provider Health** | `bioetl-provider-health-v2` | Interim provider severity/causes (merge into PD later) |
| **Data Quality** | `bioetl-dq-v2` | DQ status, reasons, threshold |

Retired product UIDs (Phase 4): `bioetl-workflow-overview`, `bioetl-alerts-slo`
(workflow band lives under Pipeline Diagnostics; alerts triage under Overview).

## Navigation contract

Bus targets **3–4** peers (panel `id=1000`). Typical diagnosis ≤2 hops from Overview.

Refresh: **60s**. Run context (ID / Processed Records) is **collapsed** — expand only
when exact-run accounting is required.

## Scenarios

| ID | Question | Path | Pass criteria |
| --- | --- | --- | --- |
| **S1** | What needs attention? | Overview | Status + First Action on first paint; no need to open L1 |
| **S2** | Pipeline / stage blocked? | Overview → Pipeline Diagnostics | Runtime Blockers / Error Rate ≤2 hops |
| **S3** | Which provider / why? | Overview → Provider Health (or PD → Provider) | Severity matrix + top causes on first paint |
| **S4** | DQ / rejects / contracts? | Overview → Data Quality | Status + reasons + threshold on first paint; rows via `bioetl quarantine inspect` |
| **S5** | Safe to replay / resume? | Overview → Trust | Replay Safety, Manifest/Ledger Integrity, Telemetry Missing on first paint; identity in collapsed row |
| **S6** | What is firing? | Overview → expand **Alert/SLO Triage** | ≤1 hop from Overview (no separate Alerts UID) |

## Offline dry-run record (2026-07-27)

| Scenario | Actions (panel/nav hops) | Notes |
| --- | --- | --- |
| S1 | 0 | Status + First Action present on `bioetl-overview-v2` first screen |
| S2 | 1 | Nav → Pipeline Diagnostics; Status + Runtime Blockers + Error Rate first paint |
| S3 | 1 | Nav not required if coming from PD; Provider first paint has matrix/causes |
| S4 | 1 | DQ Status + Inspect DQ Current Reasons + Threshold first paint |
| S5 | 1 | Trust safety cards first paint; Identity evidence collapsed |
| S6 | 1 | Expand Overview Alert/SLO Triage row |

**Fail criteria checked offline:** no dual Status twins; first-paint Ops HTTP = 0;
no first-screen `$__range` / `${__range_s}`; max first-screen expr ≤200 (budget check green).

Live TTV ≤3s is **Should** and requires the monitoring stack; not required for this
closeout.

## CLI forensic replacements

| Need | Command / surface |
| --- | --- |
| Quarantine / reject rows | `bioetl quarantine inspect` |
| Checkpoint / manifest | Control-plane runbooks under `docs/05-operations/runbooks/` |
| Exact-run accounting | Expand **Run context** row or Ops HTTP `/ops/...` |

## Related

- Epic: #6570
- Budgets: `docs/03-guides/dashboards/contracts/performance-budgets.yaml`
- Check: `python -m scripts.engineering.qa check-dashboard-performance-budgets`
