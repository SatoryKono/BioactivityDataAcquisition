> Archived snapshot. The maintained guide remains at
> [DUX3 audit selection notes](../../../03-guides/dashboards/dux3-audit-selection-notes.md).

# DUX3 audit selection notes (#7054)

**Issue:** #7054 (DUX3-01)  
**Audit:** `grafana-ux-audit-20260729-085334`
**Inventory:** `docs/03-guides/dashboards/dux3-first-screen-inventory.json`

## Reproducible selection (screenshot audit)

| Variable | Value |
| --- | --- |
| workflow | `chembl_baseline` |
| pipeline | `chembl_assay` |
| run_type | `backfill` |
| run_id | selected exact run from audit (example shown as `70f67d7e…`) |
| provider | empty on Provider Health path that produced VALID_EMPTY / 0 checks |
| Grafana range | Last 12 hours |
| refresh | board default |

## P0 screenshot claims — FACT vs needs-inspector

| Claim | Shot | Classification | Notes |
| --- | --- | --- | --- |
| Runtime Status OK + SCRAPING + Gold accounting co-visible | S5 | **FACT** layout; **INFERENCE** operator confusion | JSON separates telemetry confidence vs RUN accounting (DSA-05); needs visual non-peer treatment |
| Incident suspect pipeline ≠ selected pipeline | S2 | **FACT** if table shows other pipeline; **needs-inspector** for query filter | Label WORKFLOW/GLOBAL when unfiltered |
| DQ UNKNOWN + VALID_EMPTY + dual 100% | S3 | **FACT** visual contradiction risk | NOW scores ≠ RUN accounting; demote peer 100% cards |
| Provider 0/0 green + freshness UNKNOWN | S4 | **FACT** risk via thresholds | Ban green zero-without-denominator (DUX3-03) |
| Trust Replay Safety OK vs overall INCOMPLETE | S7 | **FACT** co-visibility | Qualify Safety with evidence coverage |
| Red expected zeros on Processed Records | S7 | **needs-inspector** for exact override | Ban red expected absence |
| ID/Processed Records burn first viewport | multi | **partially residual** | Nested in collapsed rows on non-Run boards; keep collapsed + Run Explorer hub |

## Query Inspector targets (for live pass)

1. Runtime `#` Status + Metrics Evidence / SCRAPING chip  
2. Provider Healthy Checks / Failure Rate / Freshness  
3. DQ current status + volume-weighted score stats  
4. Trust Replay Safety + Status  
5. Incident ranked/active DQ suspect table transforms  

Live inspector exports are optional when Grafana is up; static inventory is authoritative for panel geometry.

## Audited selection declaration

This residual wave treats the table above as the **canonical operator path** for
acceptance screenshots and proxy remeasure (DUX3-32 / DUX3-35).
