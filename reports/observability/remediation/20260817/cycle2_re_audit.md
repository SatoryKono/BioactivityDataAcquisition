# Cycle-2 bounded re-audit — DASH-CYCLE-005

Date: 2026-08-17. Branch: `fix/dash-cycle1-8944`. Issue: #8948.

Selectors: `workflow=chembl_baseline`, `pipeline=chembl_assay`,
`run_type=backfill`, `run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b`.

## Repaired D6 subset (3010 / 9402 / 9403)

Grafana Infinity proxy against the same Ops HTTP backend:

| Panel | Request | Result |
| --- | --- | --- |
| 3010 Recent Runs | `pipeline=chembl_assay&limit=4` | `index_state=ok`, 4 items, exact run first |
| 9402 Identity | `pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-…` | 9 rows |
| 9403 Processed Records | same scope | 11 accounting rows |
| 3010 with `pipeline=unknown` or literal `$pipeline` | valid_empty | fail-closed empty, not QUERY ERROR |
| 9402 with `run_id=-` | 0 rows | contractual `SELECT RUN` |

Static JSON: `noValue` has no `$pipeline` / `$workflow`; panel 3010/3021 have
`var-run_id=${__value.raw}` data links. Tests:
`test_run_explorer_novalue_has_no_uninterpolated_variables`,
`test_run_explorer_recent_runs_bind_run_id_via_data_link`.

Query-execution errors on this subset: **0**.

## DASH-CYCLE-003 gate

`python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check`
wrote **235** rows. `report-dashboard-inventory --check` passed.

## DASH-CYCLE-002 live Prom (after bioetl recreate)

| Probe | Value |
| --- | --- |
| `up{job="bioetl"}` | 1 |
| `count(bioetl_pipeline_runs_total{pipeline="chembl_assay",run_type="backfill"})` | 2 |
| `bioetl_runtime_trust_gap_status_10m` | 0 |
| `/health/ready` `checks.current_metrics.state` | `aligned` |

Do **not** read residual `UNKNOWN` on D1–D5 first-screen cards as a UI defect
if a given series is still semantically empty. Trust-gap CRIT from cycle-1 is
cleared on Prometheus.

## Visual matrix (light / 200% / 213 NV)

Not run as a browser matrix this pass. Remaining detail panels stay
**Not Verifiable**, not FAIL. Cycle 1 already forbade certifying that matrix
from first-screen evidence alone.

## Artifacts

- `wp0_run_explorer_inspect.md` and `wp0_*.json`
- `cycle2_prom_trust_gap.json`
- `cycle2_prom_pipeline_runs_count.json`
- `cycle2_processed_records.json`
