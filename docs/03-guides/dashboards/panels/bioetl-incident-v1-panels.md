# BioETL Incident Workspace - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-incident-v1.json`
**UID:** `bioetl-incident-v1`

## Overview

Incident Workspace (DRM residual). Read-only triage: Active Suspects by domain,
current alerts snapshot, and range alert-state history. Reuses existing recording
rules only. Not a persistent working record. Not Grafana Drilldown Investigations.

## Key Panels

### 1. Navigate Dashboards
- **Type:** Text
- **Purpose:** Full portfolio bus 0–6; current disabled.
- **Data sources:** Static HTML + panel links.

### 2. Understand Incident Scope
- **Type:** Text
- **Purpose:** Incident scope summary (workflow/pipeline/run_type/provider filters).
- **Data sources:** Dashboard variables and operator copy.

### 3. Monitor Incident Status
- **Type:** Stat
- **Purpose:** Worst-of L0 status for selected pipeline/run_type.
- **Data sources:** `bioetl_l0_status`
- **Mappings:** `0=OK`, `1=WARN`, `2=CRIT`, `3/null=UNKNOWN` (labelled; never bare numeric). Threshold step at `3` is gray.

### 3.1 Suspect / alert table color policy
- Default cell display is plain text (`auto`).
- Severity `color-background` applies only via field overrides on `Value` columns.
- Time / alertname / pipeline / provider / reason identity fields MUST NOT inherit table-wide severity paint.

### 4. Start Incident Triage
- **Type:** Text
- **Purpose:** ≤4 operator steps; honest read-only bounds; hops via Navigation bus.
- **Data sources:** Static operator copy.

### 5. Inspect Ranked Suspects
- **Type:** Table (primary first-screen localization)
- **Purpose:** Cross-domain ranked suspects (Runtime / Provider / DQ) with domain label and scoped handoff links.
- **Data sources:** `bioetl_runtime_current_blocker_reason`, `bioetl_provider_current_cause`, `bioetl_dq_current_reason` (merged instant tables)
- **Visible columns:** Domain, Pipeline, Reason, and Signal. Merge bookkeeping
  fields (`Time`, `Value`, and Grafana series aliases) are hidden.
- **Empty:** `VALID_EMPTY — no active suspects across domains`

### 5b. Domain Suspect Details (collapsed row)
- **Runtime / Provider / DQ tables** remain as forensic detail under a collapsed row (not peer first-screen verdicts).
- Each domain table keeps a data link to its workspace.
- `Inspect DQ Suspects` hides the instant-query Time field and reserves width for
  the complete `Reason`; visible fields are `Pipeline`, `Reason`, and `Signal`.

| ID | Panel title |
| --- | --- |
| 2099 | Domain Suspect Details |
| 2002 | Inspect Runtime Suspects |
| 2003 | Inspect Provider Suspects |
| 2004 | Inspect DQ Suspects |

### 8. Monitor Current Alerts
- **Type:** Table
- **Purpose:** Instant ALERTS snapshot (firing|pending). `Active Alerts` is a
  neutral multiplicity count, never an inferred severity. Not a range timeline.
- **Data sources:** Prometheus `ALERTS` (instant)

### 9. Track Alert State History
- **Type:** State timeline
- **Purpose:** Range ALERTS history — same temporal chain as Current Alerts (now);
  not a persistent incident log.
- **Data sources:** Prometheus `ALERTS` (range)
- **Presentation:** Full dashboard width with fixed firing/pending colors and no
  duplicate legend; the wider lane prevents alert-state labels from colliding.

### 10. Assess Impact & Confidence
- **Type:** Text
- **Purpose:** Structured impact/confidence template; no scored ranking claims;
  no owner/ack write-path.
- **Data sources:** Static operator copy.
