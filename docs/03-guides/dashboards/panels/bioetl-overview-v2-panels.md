# BioETL Run Overview — Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

Run Overview assesses one persisted Run ID. Time range and CURRENT fleet status
never prove this run succeeded. Live runtime/provider/control-plane metrics are
in Incident Workspace. Missing selection is SELECT RUN; absent evidence is
UNKNOWN or INCOMPLETE; failed requests remain QUERY ERROR.

## Review Run Identity

Table `9300` uses BioETL Ops HTTP `/ops/observability/selected-run-status`;
this is not a Prometheus panel. Five fixed parameters retain the full Run ID,
Pipeline, Run Type, Started at with saved UTC offset, and Total Run Duration.
Cell inspection preserves full values. There is no pagination or omitted source row:
the JSONata projection contains exactly those five parameters.

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

Table `9481` preserves saved check result and reason. Missing performed checks are
UNKNOWN. No API check is distinct from a successful remote probe.

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
| 9480 | Review Provider Evidence | table |
| 9481 | Review Provider Check | stat |
| 9460 | Inspect Selected Run Stages | table |
| 9482 | Review Contract Exclusions | canvas |
| 9483 | Review FK Comparison Scope | table |
<!-- END SHIPPED PANEL INVENTORY -->
