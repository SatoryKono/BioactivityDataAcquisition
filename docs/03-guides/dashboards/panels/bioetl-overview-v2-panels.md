# BioETL Run Overview — Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

Run Overview separates two scopes. Saved evidence assesses one persisted Run ID;
missing selection is SELECT RUN, absent evidence is UNKNOWN or INCOMPLETE, and
failed requests remain QUERY ERROR. GLOBAL / CURRENT alerts assess the fleet
independently of that selection. They never prove this run succeeded or change
its saved verdict. Incident Workspace owns incident triage and fleet diagnostics.

## Monitor Global Alerts — LA-06 (#12940)

Panel `2005` is an always-expanded root table at `y=18`, copied by
`render_nav_bus` from Incident Workspace's global alert donor. It reads the
existing `bioetl_incident_global_alerts` recording rule, which evaluates the
same expression as the donor. Its query does not
use Run ID, Pipeline, Provider, Workflow or Run Type selections. The summary
retains the donor's descending priority order and two-row limit, so critical
fleet alerts remain visible even when no saved run can be assessed. The
`Open Incident Workspace (all global alerts)` action resets the destination to
all workflows/pipelines/run types and Run ID `-`, retaining the time range.

Collapsed row `32005` is last, after the saved-run panels, and holds full table
`22005`. Both alert tables independently read `bioetl_incident_global_alerts`;
the full table has no row limit. A Dashboard-datasource consumer inside a
collapsed Grafana Scenes row can hide its source summary, so this pair does not
share a panel query runner. Expanding the full list makes every alert available
without changing the selected-run context. Provider and stage blocks move together five rows down;
their sizes, relative placement, queries and the upper saved-run layout remain.

Local validation covers JSON, query independence, donor parity, complete-list
access, non-overlapping geometry and regeneration. Live v2 rendering with
BioETLPipelineInfrastructureValidationFailed and BioETLDataFreshnessLagCritical
was recorded as NOT_VERIFIABLE under owner decision 175 for the original LA-06
delivery. Isolated 100000 was then an operating legacy generation without an
Overview JSON/generator in this checkout; neither generation had been
live-validated by that delivery. The owner subsequently confirmed retirement of
Isolated. Current v2 acceptance must inspect the complete page with the full-list
row collapsed and no selected Run ID, in addition to individual panel renders.

## Review Run Identity

Table `9300` consumes the identity frame from Overview donor `9002` through the
`-- Dashboard --` datasource. Donor `9002` loads BioETL Ops HTTP
`/ops/observability/selected-run-status`; this is not a Prometheus panel. Five
fixed parameters retain the full Run ID, Pipeline, Run Type, Started at with
saved UTC offset, and Total Run Duration. Cell inspection preserves full values.
There is no pagination or omitted source row: the JSONata projection contains
exactly those five parameters.

## Review Overall Verdict

Stat `9604` repeats the saved run verdict beside the scope banner. It neither
infers fleet health nor authorizes replay. UNKNOWN remains neutral.

## Review Selected Run Status

Table `9603` shares the source response of `9002` through the Dashboard datasource.
Processing result, saved trust, and reason stay distinct.

## Review Run Domains

Table `9002` displays six fixed saved domains. Reasons wrap and full values remain
inspectable. Open Control Plane, Open Data Quality, and Open Provider Evidence
retain workflow, pipeline, run type, Run ID, and time range.

## Review Provider Evidence

Table `9480` uses saved provider evidence for the selected run. Cached Bronze
without a remote probe is No API check; it is not a claim of live provider health.

## Review Provider Check

Stat `9481` reduces `check_result_display` from the shared selected-run donor
(same field as Review Provider Evidence). Cached Bronze without a remote probe
shows —. Missing performed checks are UNKNOWN. No API check is distinct from a
successful remote probe.

## Inspect Selected Run Stages

Table `9460` combines HTTP stage diagnostics with saved pipeline-run accounting.
Quarantined, excluded, deduplicated, and filtered outcomes remain distinct;
percentages require a valid stage denominator.
An unexplained stage balance remains FAILING even when execution succeeded.
The displayed Trust exposes this conflict without rewriting the saved verdict.
ChEMBL synthetic protein-class root nodes are counted as Silver filtering with
reason `FILTERED_OUT_SILVER:protein_class_id` in new reports.

## Review Contract Exclusions

Native canvas `9482` shows selected-run exclusion status and rate. Limits come
from the pipeline configuration used at generation, not historical overrides.
Incomplete counters are UNKNOWN. Quarantine/filter/dedup are separate outcomes.
An OK exclusion rate does not certify stage accounting integrity.

## Review FK Comparison Scope

Table `9483` reads FK comparison evidence from the exact linked parent workflow.
Explicit standalone identity is N/A; a persisted plan containing only pipeline
steps or upstream summaries is also N/A. Missing identity, missing plans,
expected-but-unrecorded comparisons, and unknown transform kinds remain UNKNOWN.
Snapshot pins, limits, row scopes and results describe the FK comparison, not the
pipeline extraction limit. Historical reports remain unchanged.

<!-- BEGIN SHIPPED PANEL INVENTORY -->
## Current shipped panel inventory

Generated from the dashboard JSON. Earlier sections explain panel semantics; this table identifies the panels shipped in the current dashboard.

| ID | Title | Type |
| --- | --- | --- |
| 99 | Inspect Scope & Evidence | text |
| 9604 | Review Overall Verdict | stat |
| 9002 | Review Run Domains | table |
| 9603 | Review Selected Run Status | table |
| 9300 | Review Run Identity | table |
| 32005 | Browse Global Alerts | row |
| 22005 | Monitor Global Alerts (Full) | table |
| 2005 | Monitor Global Alerts | table |
| 9480 | Review Provider Evidence | table |
| 9481 | Review Provider Check | stat |
| 9460 | Inspect Selected Run Stages | table |
| 9482 | Review Contract Exclusions | canvas |
| 9483 | Review FK Comparison Scope | table |
<!-- END SHIPPED PANEL INVENTORY -->
