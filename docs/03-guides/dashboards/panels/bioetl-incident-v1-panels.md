# BioETL Incident Workspace - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-incident-v1.json`
**UID:** `bioetl-incident-v1`

## Overview

Incident Workspace (DRM residual). Read-only triage: Active Suspects by domain,
current alerts snapshot, and range alert-state history. Reuses existing recording
rules only. Not a persistent working record. Not Grafana Drilldown Investigations.

## Key Panels

### 2. Understand Incident Scope
- **Type:** Text
- **Purpose:** Explicit GLOBAL fleet triage scope. Pipeline and Run ID selections
  do not filter ranked suspects; selected-run evidence is separate.
- **Data sources:** Dashboard variables and operator copy.

### 3. Monitor Scope Status
- **Type:** Stat
- **Purpose:** Worst-of L0 status for selected pipeline/run_type.
- **Data sources:** `bioetl_l0_status`
- **Mappings:** `0=OK`, `1=WARN`, `2=CRIT`, `3/null=UNKNOWN` (labelled; never bare numeric). Threshold step at `3` is gray.

### 3.1 Suspect / alert table color policy
- Default cell display is plain text (`auto`).
- Severity styling applies only through the explicit severity field override.
- Time / alertname / pipeline / provider / reason identity fields MUST NOT inherit table-wide severity paint.

### 4. Start Incident Triage
- **Type:** Text
- **Purpose:** Explain CURRENT global ranking, equal-severity ties and unverified
  cause, impact and event age; hops via Navigation bus.
- **Data sources:** Static operator copy.

### 5. Inspect Ranked Suspects
- **Type:** Table (primary first-screen localization)
- **Purpose:** Cross-domain ranked suspects (Runtime / Provider / DQ) with
  shipped severity priority, domain/signal basis, next action, and scoped handoff links.
- **Data sources:** One instant union of `bioetl_incident_ranked_runtime`,
  `bioetl_incident_ranked_provider` and `bioetl_incident_ranked_dq`.
- **Ranking:** shipped `severity` labels (`failing`/`crit`=2, `degraded`/`warn`=1).
  Priority 0 is `telemetry_gap` / UNKNOWN. Boolean `> 0` activation is not the rank.
- **Visible columns:** Rank, Severity, Confidence, Object, Signal, Action, Details, Domain.
  Value sorts descending before the global top-five limit and is displayed as
  Severity. Rank is a one-based row index; equal severity has equal urgency.
  Object combines pipeline/provider; raw labels remain accessible in Inspect.
  Confidence is UNVERIFIED and does not claim a measured causal probability.
- **Action:** Opens the indicated domain workspace for the row's Pipeline,
  preserving the time range and applicable filters while clearing the selected Run ID.
- **Details:** Offers a separate **Inspect value** control for the original action
  value. Inspecting it leaves the Incident Workspace open; Action performs the
  diagnostic handoff. Details uses available width without a fixed reservation.
- **Empty:** `VALID_EMPTY — no active suspects across domains`

### 5b. Domain Suspect Details · GLOBAL / CURRENT (collapsed row)
- **Runtime / Provider / DQ tables** remain as forensic detail under a collapsed row (not peer first-screen verdicts).
- Domain detail and ranked suspects share GLOBAL CURRENT scope. An empty domain
  means no active domain rows; it does not contradict another domain's suspect.
- Each domain table keeps a data link to its workspace.
- `Inspect DQ Suspects` hides the instant-query Time field and reserves width for
  the complete `Reason`; visible fields are `Pipeline`, `Reason`, and `Signal`.

| ID | Panel title |
| --- | --- |
| 2099 | Domain Suspect Details · GLOBAL / CURRENT |
| 2002 | Inspect Runtime Suspects |
| 2003 | Inspect Provider Suspects |
| 2004 | Inspect DQ Suspects |

### 7. Review Alert Evidence
- **Type:** Row (**collapsed by default**, `id=2020`)
- **Purpose:** Progressive disclosure for range alert history and
  impact/confidence guidance after ranked-suspect triage. Current alerts
  (`id=2005`) stay on the first screen.
- **Data sources:** Nested Prometheus and static evidence panels below.

### 8. Monitor Global Alerts
- **Type:** Table (first-screen, `id=2005`, below ranked suspects)
- **Purpose:** Instant ALERTS snapshot (firing|pending) with a runbook link.
  Limited to three rows. `Active Alerts` is a
  neutral multiplicity count, never an inferred severity. Not a range timeline.
- **Data sources:** Prometheus `ALERTS` (instant)

### 9. Track Alert State History
- **Type:** State timeline
- **Purpose:** Range ALERTS history — same temporal chain as Current Alerts (now);
  not a persistent incident log.
- **Data sources:** Prometheus `ALERTS` (range)
- **Presentation:** Full dashboard width, eight grid rows and a 360 px label
  axis for complete alert names plus firing/pending state. Outlined intervals
  use FIRING red and PENDING orange with an explicit legend; missing samples
  remain gaps. State words are not repeated inside narrow bands. Adjacent equal
  states merge, while range timestamps remain available in the timeline tooltip.

### 10. Assess Impact & Confidence
- **Type:** Text
- **Purpose:** Structured impact/confidence template; no scored ranking claims;
  no owner/ack write-path.
- **Data sources:** Static operator copy.

## Additional shipped panels
### 11. Inspect Selected Run Summary

Shipped in `bioetl-incident-v1.json`.
### 12. Review Selected Run Status

Shipped in `bioetl-incident-v1.json`.

### 100. Browse Global Suspects

Complete evidence is available in the collapsed detail group. The table reuses the source panel response before transformations, keeps all rows, and shows the total through native pagination. It issues no duplicate backend query.

### 101. Inspect Global Suspects (Full)

Complete evidence is available in the collapsed detail group. The table reuses the source panel response before transformations, keeps all rows, and shows the total through native pagination. It issues no duplicate backend query.

### 102. Browse Global Alerts

Complete evidence is available in the collapsed detail group. The table reuses the source panel response before transformations, keeps all rows, and shows the total through native pagination. It issues no duplicate backend query.

### 103. Monitor Global Alerts (Full)

Complete evidence is available in the collapsed detail group. The table reuses the source panel response before transformations, keeps all rows, and shows the total through native pagination. It issues no duplicate backend query.

## Saved evidence and discovery panels

| ID | Title | Purpose |
| --- | --- | --- |
| 9450 | Inspect Saved Run Evidence | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9460 | Inspect Selected Run Stages | Saved stage rows joined with Quarantined, Excluded, Deduplicated and Filtered out counters from the exact report's per-stage funnel removals; untracked stages stay UNKNOWN. |
| 9451 | Inspect Selected Run Domains | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9452 | Inspect Selected Run Identity | Saved exact-run evidence; expand for identity, version, reasons and actions. |

The first-window ranked-suspect and current-alert tables show up to two rows;
the panel links open the unrestricted full lists. Alert history paginates
at eight series per page while preserving complete alert and scope labels.

### 99. Inspect Global Signal Measurements

GLOBAL / TIME RANGE. Runtime lag and non-validation backlog operands with thresholds, window and evaluation time. Missing observed/published timestamps leave freshness unverified.

<!-- BEGIN SHIPPED PANEL INVENTORY -->
## Current shipped panel inventory

Generated from the dashboard JSON. Earlier sections explain panel semantics; this table identifies the panels shipped in the current dashboard.

| ID | Title | Type |
| --- | --- | --- |
| 9400 | Understand Incident Scope | text |
| 9401 | Monitor Scope Status | stat |
| 2001 | Start Incident Triage | text |
| 2010 | Inspect Ranked Suspects | table |
| 2005 | Monitor Global Alerts | table |
| 2020 | Review Alert Evidence | row |
| 2006 | Track Alert State History | state-timeline |
| 2007 | Assess Impact & Confidence | text |
| 2099 | Domain Suspect Details · GLOBAL / CURRENT | row |
| 2002 | Inspect Runtime Suspects | table |
| 2003 | Inspect Provider Suspects | table |
| 2004 | Inspect DQ Suspects | table |
| 22011 | Inspect Global Signal Measurements | table |
| 2100 | Inspect Selected Run Summary | row |
| 2101 | Review Selected Run Status | table |
| 8808 | Pipeline fleet and range, not this Run ID | row |
| 18940 | Monitor Pipeline Status | stat |
| 9101 | Review Runtime Blockers | table |
| 9102 | Monitor Coverage | stat |
| 2460 | Review Stage Progress | table |
| 9463 | Review Total Run Duration | stat |
| 238 | Track Stage Backlog Trend | timeseries |
| 207 | Track Phase Duration | timeseries |
| 239 | Track Pipeline Duration | timeseries |
| 2541 | Review Runtime Escalation | text |
| 237 | Monitor Worst Stage Lag | stat |
| 16 | Monitor Active Blocker Count | stat |
| 205 | Monitor Failed Runs | stat |
| 230 | Monitor Pipeline Alerts | stat |
| 9996 | Track Failed Workflow Runs | stat |
| 236 | Monitor No-Records Runs | stat |
| 9997 | Track Failed Workflow Steps | stat |
| 21 | Monitor Memory Pressure | stat |
| 256 | Review Errors by Stage & Code | table |
| 241 | Compare Records by Stage & Run Type | table |
| 891 | Monitor Replay | stat |
| 892 | Track Checkpoint | stat |
| 893 | Monitor Ledger | stat |
| 907 | Monitor Telemetry | stat |
| 2542 | Review Cross-Domain Handoffs | text |
| 240 | Track Records by Stage / Interval | timeseries |
| 4 | Inspect DQ Alert Conditions | stat |
| 5 | Inspect Control Plane Alerts | stat |
| 6 | Inspect Provider Alerts | stat |
| 9991 | Start Pipeline Triage | text |
| 894 | Review Coverage Limits | text |
| 259 | Inspect Global Provider Alert Conditions | stat |
| 908 | Review Observed Terminal Counters | table |
| 7 | Inspect Entities Stale Over 24h | stat |
| 8804 | Track Global Read Failures | stat |
| 136 | Monitor Global Read Failures (30m) | stat |
| 122 | Track Missing Lineage | stat |
| 137 | Track Lineage Failures | stat |
| 2 | Track Ledger Failures | stat |
| 130 | Track Replay Blockers | stat |
| 242 | Inspect Active Runtime Blocker Detail | table |
| 2461 | Inspect Current Missing Stage Signals | table |
| 2543 | Review Global Process Signals | text |
| 8806 | Compare Global Reads by Store | timeseries |
| 1 | Track Manifest Failures | stat |
| 3 | Track Incompatibilities | stat |
| 104 | Track Unreconstructable | stat |
| 138 | Review Missing Lineage by Layer | table |
| 120 | Track Replay Drift | stat |
| 132 | Monitor Manifest (30m) | stat |
| 209 | Track Global Shutdown Starts | timeseries |
| 101 | Track Load Failures | stat |
| 133 | Monitor Ledger (30m) | stat |
| 210 | Track Global Shutdown Completions | timeseries |
| 102 | Track Save Failures | stat |
| 9491 | Inspect Telemetry Coverage | stat |
| 103 | Track Global Admin Failures | stat |
| 111 | Track Global Read Latency | timeseries |
| 131 | Track Observed Manifest Write Increments | timeseries |
| 121 | Track Peak Replay Lag | stat |
| 107 | Compare Global Audit Write Outcomes | timeseries |
| 134 | Track Replay Drift by Type | timeseries |
| 9105 | Track Stage Lag | timeseries |
| 8805 | Compare Checkpoint Outcomes | timeseries |
| 108 | Compare Global Audit Query Outcomes | timeseries |
| 135 | Track Replay Lag | timeseries |
| 8807 | Compare Ledger Appends by Type & Status | timeseries |
| 243 | Inspect Stage Expectedness | table |
| 105 | Track Checkpoint Save Latency | timeseries |
| 109 | Track Global Audit Write Latency | timeseries |
| 106 | Track Global Checkpoint Admin Latency | timeseries |
| 110 | Track Global Audit Query Latency | timeseries |
| 220 | Monitor Runtime Error Rate | stat |
| 112 | Compare Lineage Persistence Outcomes | timeseries |
| 32010 | Browse Global Suspects | row |
| 22010 | Inspect Global Suspects (Full) | table |
| 32005 | Browse Global Alerts | row |
| 22005 | Monitor Global Alerts (Full) | table |
| 9450 | Inspect Saved Run Evidence | row |
| 9460 | Inspect Selected Run Stages | table |
| 9451 | Inspect Selected Run Domains | table |
| 9452 | Inspect Selected Run Identity | table |
| 9700 | Inspect Current Workflow Evidence | row |
| 9701 | Review Current Workflow Evidence | table |
<!-- END SHIPPED PANEL INVENTORY -->
