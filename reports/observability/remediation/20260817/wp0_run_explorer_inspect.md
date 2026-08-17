# WP-0 — Run Explorer Inspect vs direct Ops HTTP

Date: 2026-08-17. Branch: `fix/dash-cycle1-8944`.  
Issue: #8946. Selectors: `pipeline=chembl_assay`, `run_type=backfill`,
`run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b`.

Grafana was healthy (`:3000` v12.0.0). BioETL Ops HTTP was healthy (`:8000`).
Panel JSON URLs use `${pipeline}` / `${run_id}`. `fieldConfig.noValue` is **not**
interpolated by Grafana.

## Direct Ops HTTP (host :8000)

| Call | Result |
| --- | --- |
| `GET /ops/observability/pipeline-run-reports?pipeline=chembl_assay&limit=4` | `index_state=ok`, 4 items, first `eb1a6a55-…` |
| `GET /ops/control-plane/identity-table?pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-…` | 9 identity rows, `selected_run_id` set |
| `GET /ops/observability/processed-records?pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-…` | 11 accounting rows |
| `GET /ops/observability/pipeline-run-report?pipeline=chembl_assay&run_id=eb1a6a55-…` | report body present (`layers`, `funnel`, `reconciliation`) |

Artifacts: `wp0_recent_runs.json`, `wp0_identity_table.json`,
`wp0_processed_records.json`, `wp0_pipeline_run_report.json`.

## Grafana Infinity proxy (same backend, :3000 → `bioetl-ops-http`)

| Request query string | Result | Matches cycle-1 UI |
| --- | --- | --- |
| `pipeline=chembl_assay&limit=4` | `index_state=ok`, 4 runs including the exact run | populated browse table |
| `pipeline=$pipeline` (literal) | `index_state=valid_empty`, count=0 | `VALID EMPTY` + dollar token in old `noValue` |
| `pipeline=unknown&limit=4` | `index_state=valid_empty`, count=0 | default Prom pipeline variable |
| identity `pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-…` | 9 rows | selected-run filled |
| identity `run_id=-` | 0 rows | contractual `SELECT RUN` |

## Which mechanisms fired

1. **Proven:** `noValue` stored `'$pipeline'`. Grafana does not interpolate it.
   A valid-empty query (unknown / literal `$pipeline`) therefore rendered the
   dollar token. Fixed: static copy, no `$` tokens.
2. **Proven:** identity/accounting with `run_id=-` return zero rows → `SELECT RUN`.
   Panel 3010 had no data link writing `var-run_id`. A table highlight does not
   bind the dashboard variable. Fixed: Run-column data link sets `var-run_id`
   and `var-pipeline` from the row.
3. **Proven as contributing:** `pipeline=unknown` (Prom default while the
   universe is empty) yields valid-empty browse even though `chembl_assay`
   reports exist. The data link now also writes `var-pipeline` from the row so
   a click does not depend on the Prom universe. Pipeline variable source is
   unchanged (selector-contract shared Prom universe).

## Conclusion

Backend and Grafana proxy are healthy when variables are interpolated to
`chembl_assay` + the exact `run_id`. Cycle-1 `SELECT RUN` / literal `$pipeline`
is binding + `noValue`, not a missing store.
