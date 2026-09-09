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

### 3. Monitor Incident Status
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

### 8. Monitor Current Alerts
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
### 12. Review Selected Run Summary

Shipped in `bioetl-incident-v1.json`.
