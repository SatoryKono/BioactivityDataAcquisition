## Summary

Provider Health first-screen Status / Severity Matrix / Telemetry Freshness show **UNKNOWN / No data** because Prometheus has **zero** `bioetl_provider_current_status` series.

## Evidence (live 2026-07-29)

- `bioetl_provider_current_status` → n=0
- Recording rule depends on `bioetl_provider_health_status` + universe helpers
- bioetl scrape target was `up` but provider health raw series absent

## Expected

- Either emit/scrape `bioetl_provider_health_status` (or equivalent) so recording rules populate
- Or dashboard empty-state must say **Telemetry missing / no provider checks** (not bare UNKNOWN without reason)

## Acceptance

- With healthy bioetl metrics path, Provider Status is labelled and non-empty for known providers
- Missing series surface SELECTION_REQUIRED / TELEMETRY_MISSING grammar (not silent UNKNOWN)

## Related

PFILL epic #7158 (P0 closed). This is P1 residual.
