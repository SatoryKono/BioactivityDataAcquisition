# BioETL Control Plane v1 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-control-plane-v1.json`

## Обзор

Dashboard `2. Replay Readiness` is the shipped exact-replay workspace.
Shipped dashboard JSON is the source of truth. This page describes only panels
present in that JSON.

The first-window answer `9422` (`Review Exact Replay Readiness`) is a saved
exact-replay assessment, not current Prometheus health. Its missing value is
`UNKNOWN`, never `READY`. `SELECT RUN` means no Run ID is selected. Source
unavailable means a failed request or an unavailable backend. `UNSUPPORTED`,
`UNKNOWN`, and `INCOMPLETE` stay gray. Open `9423` (`Review Exact Replay
Checks`) for the recorded basis: a failed check blocks replay, and unknown is
not a pass.

`9400` (`Inspect Scope & Evidence`) points at exact replay readiness, then the
saved Trust verdict (`9418`), then retention (`9416`). Those answers use the
selected Run ID. `9418` keeps `processing_status` (saved ETL outcome) separate
from `trust_status` (historical Trust). Trust status does not authorize replay.

Panel `1000` (`Navigate Dashboards`) is the shared navigation band.

## Variable contract

- Panels inherit the shared shell selectors: `workflow`, `pipeline`,
  `run_type`, `run_id`.
- HTTP tables use `BioETL Ops HTTP`. Panels `9422` and `9423` use the built-in
  Grafana `-- Dashboard --` datasource.
- This dashboard ships no Prometheus `expr`.

## Shipped panels

| ID | Title | Type | Datasource | Purpose |
| --- | --- | --- | --- | --- |
| 1000 | Navigate Dashboards | text | Static | Shared navigation band. |
| 9400 | Inspect Scope & Evidence | text | Static | Read exact replay readiness, then saved Trust, then retention. |
| 9422 | Review Exact Replay Readiness | stat | Grafana `-- Dashboard --` | Saved exact-replay assessment for the selected Run ID. |
| 9423 | Review Exact Replay Checks | table | Grafana `-- Dashboard --` | One row per readiness check. Fail blocks replay. |
| 9408 | Review Replay Evidence | table | BioETL Ops HTTP | Identity anchors for this run. Presence is not verification. |
| 9418 | Review Selected-Run Trust | table | BioETL Ops HTTP | Saved processing outcome and historical Trust assessment. |
| 9430 | Inspect Manifest / Lineage / Retention | row | Static | Groups manifest, lineage, and retention tables. |
| 9414 | Review Manifest Validation | table | BioETL Ops HTTP | Manifest parse, structure, schema version, and contract compatibility. |
| 9415 | Review Lineage Validation | table | BioETL Ops HTTP | Lineage closure, identity consistency, cycles, and persistence profile. |
| 9416 | Review Retention Compliance | table | BioETL Ops HTTP | Policy, evidence floor, required evidence, snapshot evidence, and archive. |
| 9431 | Inspect Resume / Checkpoint | row | Static | Groups checkpoint tables. |
| 9413 | Review Checkpoint Validation | table | BioETL Ops HTTP | Checkpoint parse, schema, checksum, and required identity anchors. |
| 9406 | Compare Checkpoint Anchors | table | BioETL Ops HTTP | Runtime anchors for this run compared with its checkpoint. |

Value mappings and empty-state copy live in the panel JSON.

<!-- BEGIN SHIPPED PANEL INVENTORY -->
## Current shipped panel inventory

Generated from the dashboard JSON. Earlier sections explain panel semantics; this table identifies the panels shipped in the current dashboard.

| ID | Title | Type |
| --- | --- | --- |
| 9400 | Inspect Scope & Evidence | text |
| 9422 | Review Exact Replay Readiness | stat |
| 9423 | Review Exact Replay Checks | table |
| 9408 | Review Replay Evidence | table |
| 9418 | Review Selected-Run Trust | table |
| 9430 | Inspect Manifest / Lineage / Retention | row |
| 9414 | Review Manifest Validation | table |
| 9415 | Review Lineage Validation | table |
| 9416 | Review Retention Compliance | table |
| 9431 | Inspect Resume / Checkpoint | row |
| 9413 | Review Checkpoint Validation | table |
| 9406 | Compare Checkpoint Anchors | table |
<!-- END SHIPPED PANEL INVENTORY -->
