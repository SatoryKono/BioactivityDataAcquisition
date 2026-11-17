# BioETL Run Overview — Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

Run Overview separates two scopes. Saved evidence assesses one persisted Run ID;
an unresolved selection resolves the latest run in scope; absent evidence is UNKNOWN or INCOMPLETE, and
failed requests remain QUERY ERROR. Global alerts assess the fleet independently
of that selection: native panels use the selected period end, while the adaptive
profile evaluates its explicitly marked CURRENT panels independently. They never prove this run succeeded or change
its saved verdict. Incident Workspace owns incident triage and fleet diagnostics.

## Review Fleet Alerts — LA-06 (#12940)

Panel `2005` is an always-expanded root table at `y=18`, copied by
`render_nav_bus` from Incident Workspace's global alert donor. It reads the
existing `bioetl_incident_global_alerts` recording rule, which evaluates the
same expression as the donor. Its query does not
use Run ID, Pipeline, Provider, Workflow or Run Type selections. The table
retains the donor's descending priority order and every matching alert, with
pagination enabled at the top level and in the legacy footer. There is no
topk or row-limit transformation. The
`Open Incident Workspace (all global alerts)` action resets the destination to
all workflows/pipelines/run types and Run ID `-`, retaining the time range.

Use pagination in panel `2005` to inspect the complete list, or follow its
Incident Workspace action for incident details. Overview has no separate
collapsed full-list row; no expansion is required and there is no second query
for the same alert list. In the adaptive compact view, Next/Previous and Details
retain access to all returned rows and their complete evidence.

Local validation covers JSON, query independence, donor parity, complete-list
access, non-overlapping geometry and regeneration. Live v2 rendering with
BioETLPipelineInfrastructureValidationFailed and BioETLDataFreshnessLagCritical
was recorded as NOT_VERIFIABLE under owner decision 175 for the original LA-06
delivery. Isolated 100000 was then an operating legacy generation without an
Overview JSON/generator in this checkout; neither generation had been
live-validated by that delivery. The owner subsequently confirmed retirement of
Isolated. Current v2 verification must inspect the complete page without a
selected Run ID, exercise pagination beyond the first visible rows, and verify
the Incident handoff, in addition to individual panel renders. This protocol
does not change the historical acceptance result.

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
| 9604 | Review Saved Run Verdict | stat |
| 9605 | Review Snapshot Fleet Alerts | stat |
| 9606 | Review Processing Anchor Age · 24h / 72h · period end | stat |
| 9603 | Review Selected Run Status | table |
| 99 | Review Run Context | table |
| 9300 | Review Run Identity | table |
| 9002 | Review Run Domains | table |
| 2005 | Monitor Global Alerts | table |
| 9480 | Review Provider Evidence | table |
| 9481 | Review Provider Check | canvas |
| 9460 | Inspect Selected Run Stages | table |
| 9482 | Review Contract Exclusions | canvas |
| 9483 | Review FK Comparison Scope | table |
<!-- END SHIPPED PANEL INVENTORY -->

## Review Run Context — LA-12 (#12946)

Panel `99` shows AUTO or EXPLICIT, the actual Run ID, execution state, saved
verdict and Context checked at (Grafana query evaluation time). AUTO includes unfinished latest runs; an
explicit unavailable run stays bound rather than falling back to another run.
The context reuses the same donor frame as saved evidence, so it adds no HTTP
request and cannot describe a different snapshot. The clock is not run start,
a browser click, server cache load or catalog freshness. The block stays in
the first window; the identity table remains bounded to its existing five rows.
