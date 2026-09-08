# Operator scenarios: seven dashboards and Q1–Q3 (#10167)

## Current protocol

The primary role is the operator investigating pipeline execution and evidence.
The following page goals are proposed from shipped contracts; owner approval is
required in each measurement bundle. Assigning Astra as the operator records an
`AI_AGENT` session, not a human participant or a page-goal approval.

| Dashboard / UID | Page goal | Q1: state/object | Q2: basis/reason | Q3: first safe action |
| --- | --- | --- | --- | --- |
| Trust / `bioetl-control-plane-v1` | Decide what evidence is needed before replay/resume | State trust and replay scope | Identify missing identity/integrity evidence | Open the relevant evidence check; do not authorize replay from processing success |
| Overview / `bioetl-overview-v2` | Triage current fleet state and selected-run summary | Separate current state from selected UUID | Identify the affected domain and visible basis | Follow First Action to the matching diagnostics |
| Pipeline Diagnostics / `bioetl-runtime` | Investigate execution blockers | Separate SCRAPING from execution health | Identify blocker reason or missing telemetry | Open blocker details or the relevant runbook |
| Provider Health / `bioetl-provider-health-v2` | Identify provider impact and cause | Name provider and fleet severity | Read status reason and scope | Open provider diagnostics with allowed context |
| Data Quality / `bioetl-dq-v2` | Separate current quality from range impact | State current DQ status | Explain range rejects/threshold evidence | Open supported DQ diagnostics or CLI runbook |
| Incident / `bioetl-incident-v1` | Rank evidence-backed diagnostic hypotheses | Name incident impact and scope | Explain suspect rank, basis and confidence | Follow the suspect domain action and return |
| Run Explorer / `bioetl-run-explorer-v1` | Find a run and inspect exact-run evidence | Identify run/pipeline/workflow | Explain selected-run accounting and trust limitations | Open a real report artifact and return to the same run |

For each row execute all three questions: **21 mandatory tasks**. Q3 includes the
actual destination and return, not just naming a link. Preserve allowed variables,
fixed UTC range and explicit timezone. The ordered `0..6` navigation bus omits
the current page. Static reachability is not measured diagnostic click depth.

The recorder follows [usability-baseline-protocol.md](usability-baseline-protocol.md).
Machine-readable task IDs, roles and initial-state requirements are in
[operator-task-protocol.json](contracts/operator-task-protocol.json).
Before a session, bind fixture-specific answer keys to independently checked
evidence; unknown data must remain an explicit acceptable answer when warranted.
Do not show answer keys or target panels to an unexposed participant.

## Historical S1–S6 protocol and offline results (2026-07-27)

Everything below is retained as historical evidence. Its five-surface plan,
navigation counts and offline results do not describe current acceptance.

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
| **S3** | Which provider / why? | Overview → Provider Health (or PD → Provider) | First paint: `9101` Monitor Fleet Severity + `9107` Inspect Status Reason; `9103` Inspect Top Provider Causes is 1-hop expand of row `9106` |
| **S4** | DQ / rejects / contracts? | Overview → Data Quality | Status + threshold on first paint; expand **Selected Range · Impact & Freshness** for reasons; rows via `bioetl quarantine inspect` |
| **S5** | Safe to replay / resume? | Overview → Trust | Replay Safety, Manifest/Ledger Integrity, Telemetry Missing on first paint; identity in collapsed row |
| **S6** | What is firing? | Overview → expand **Alert/SLO Triage** | ≤1 hop from Overview (no separate Alerts UID) |

## Offline dry-run record (2026-07-27)

| Scenario | Actions (panel/nav hops) | Notes |
| --- | --- | --- |
| S1 | 0 | Status + First Action present on `bioetl-overview-v2` first screen |
| S2 | 1 | Nav → Pipeline Diagnostics; Status + Runtime Blockers + Error Rate first paint |
| S3 | 1 | Nav not required if coming from PD; first paint is `9101`+`9107`; `9103` via expand `9106` |
| S4 | 1 | DQ Status + Threshold first paint; reasons under collapsed Selected Range row |
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


## Phase 2 PromQL diet (#6574)

First-screen PromQL is budgeted by `performance-budgets.yaml` in **error** mode:

- max first-screen expression length **≤200**
- worst first-load PromQL panels **≤6**
- first-screen `$__range` refs **0**
- timeseries panels use `maxDataPoints` (~400) and min step `1m` where applicable

Recording KPIs already live under `grafana/prometheus-rules/bioetl_observability.yml`
(e.g. `bioetl_runtime_error_rate_30m`, alert-condition recordings). Prefer
`max(rule)` / thin selectors on first paint; keep long multi-`label_replace`
evidence under collapsed progressive-disclosure rows.

### Operator “Explore” hops (Prometheus Explore bookmarks)

| ID | Intent | Start from | Notes |
| --- | --- | --- | --- |
| E1 | Histogram detail (p50/p99) | Pipeline Diagnostics collapsed rows | First paint keeps p95-class cards only |
| E2 | Errors by stage | Runtime / PD | Use `bioetl_errors_total` / stage series |
| E3 | Retries | Runtime | Prefer existing retry counters |
| E4 | Active alerts | Overview → Alert triage | `ALERTS` / alert condition recordings |
| E5 | CP latency | Trust | Manifest/ledger/checkpoint series |
| E6 | Reject topk | Data Quality collapsed range rows | Quarantine/reject series; row forensics on CLI |
