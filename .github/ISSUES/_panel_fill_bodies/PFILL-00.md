## Summary

Fix **explicit dashboard panel fill errors** found by live Ops HTTP + Prometheus inspection (ID / Processed Records and related HTTP/Prom surfaces).

## Scope (from live audit)

### P0
1. Processed Records: `display_token` duplicates parameter into `value`/`percintage` (`01 bronze_records|45`)
2. Processed Records: field typo `percintage` → `percentage`
3. ID panel: `identity-table` returns `scope_resolve_timeout` placeholders while `identity-evidence` resolves same scope
4. ID panel: Provider.Entity falls back to pipeline name when unresolved
5. Wrong health dataLinks to `localhost:8081` (Ops is :8000)
6. Run Explorer browse / pipeline-run-reports empty or timeout paths

### P1
7. Provider Status/Freshness missing series → UNKNOWN
8. DQ Worst Freshness missing metric
9. Status vs accounting/alert semantic mismatches

## Constraints

- No invent metrics / no Prom `run_id` labels
- Grafana remains interface adapter; fix payload contracts in application/HTTP layer first
- Update Grafana transforms when renaming `percintage`

## Evidence

Live probes against `bioetl:8000` Ops HTTP and Prometheus (2026-07-29 session).
