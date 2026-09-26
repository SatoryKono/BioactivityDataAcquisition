# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`
**UID:** `bioetl-run-explorer-v1`

## Overview

Run Explorer is a recent-launch list with direct report access. Defaults are
Workflow=All, Pipeline=All, Run Type=All, Run ID=-. Explicit URL selections win.
The page contains navigation, a scope banner, and Inspect Recent Runs (last 10).
Selected Run Details and Browse Workflow Runs, including their nested panels,
were removed at the operator's request. Report and control-plane APIs remain
available independently of the dashboard.

## Navigate Dashboards

Chips on this page are non-interactive. Open Trust, Overview, Pipeline
Diagnostics, Provider Health, and Data Quality from the matching columns in
Inspect Recent Runs. Incoming links from other workspaces still open this list.

### 1. Understand Run Scope

The first line explains that the list shows the last ten launches by start time,
independently of the time picker. A line break before Pipeline separates this
explanation from Pipeline and SELECTED RUN context. Open Report inspects the
persisted run evidence.

### 2. Inspect Recent Runs (last 10)

- **Type:** Table, panel 3010; the only data panel on this dashboard.
- **Data source:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
  with `view=recent`; one request per refresh.
- **Rows:** Last ten launches, all shown together without pagination. Compact
  single-line cells retain full values through Inspect and full UUID links.
- **Layout:** Link-only navigation h=2, scope banner y=2/h=3, table y=5/h=12. The table
  uses the existing ten-row limit and small native cell height.
- **Selection:** Clicking Run sets that row's Workflow, Pipeline, Run Type and
  Run ID, preserving the time range and marking the matching row. It does not
  target a detail panel. Browse all pipelines restores All scopes and Run ID=-.
- **Reports:** Open report opens the exact row's Markdown file in a new tab,
  falling back to JSON. Markdown is displayed as text. Report URLs use the
  Grafana Ops HTTP proxy, independent of the selected dashboard Run ID.
  REPORT MISSING opens an explicit bilingual not-found response. A deleted
  file returns not found rather than another run's report.

## Ordering and evidence

Workflow, Pipeline and Run Type filters apply before the global ten-row limit.
Start time comes from persisted report identity or ledger start events; manifest
creation is an explicit fallback. File modification time never ranks this view.
Repeated pipelines remain separate rows. The time picker does not filter the
list. Run ID selects and marks a row rather than limiting the list to one run.

Final reports supply immutable start/status evidence. A recorded start without
a terminal event displays running as its last known lifecycle state, not proof
of a live process. Manifest-only entries remain unknown. A missing report does
not imply zero accounting.

## Exact lookup and timing

Find Run ID filters by exact UUID before the ten-row limit, within the selected
Workflow/Pipeline/Run Type. Clearing it restores the recent list. Duration uses
persisted start/completion timestamps and the same compact duration as Event
age (`10 s`, `1 m 30 s`, `16 h 53 m`). Missing start or end stays UNKNOWN;
running is not a live elapsed timer. Event age uses the last ledger event
only for running launches. Terminal launches show `completed` for Event age.
Missing or future timestamps stay UNKNOWN. Neither file mtime nor scrape time
can substitute for event evidence.

## Empty and failure states

VALID EMPTY means no matching launches. TREE_MISSING, LAYOUT_UNHEALTHY and
IDENTITY_UNHEALTHY indicate report bind/origin failures, not selector problems.
Run `python scripts/ops/runtime/docker/verify_report_bind.py` from the canonical
checkout to diagnose the report bind. Backend failures remain QUERY ERROR.

## Verification

Dashboard HTTP and semantic contracts cover the three remaining panels.
Regression checks require both removed groups to stay absent, ten rows without
pagination, a line break before Pipeline, and no links to retired detail panels.
Run dashboard readability and first-window containment tests and verify the
actual browser table with ten populated rows and working Report links.

Inspect Saved Run Evidence is not on this page. Saved domain and identity
evidence stays on Trust.

Recent Runs keeps Pipeline, the short Run ID, Processing, Trust and Report
readable in the 900-pixel view. Trust uses an Open link, never an inferred OK
from processing success. Event age remains in the query frame for Inspect
data; it is hidden from the compact table because Started already supplies
the visible timestamp. Exact Run IDs and event-age values remain unchanged.
