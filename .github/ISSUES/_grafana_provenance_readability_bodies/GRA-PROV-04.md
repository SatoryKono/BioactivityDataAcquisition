## Problem

`3. Provider Health` panel `id=9400` uses three dense `12px` lines. At
1366×768 the last line approaches the right boundary, reducing readability of
the missing-telemetry action.

## Proposed change

Apply the shared Data Quality Provenance design with:

- headline: **Which provider is degraded, and why?**
- scope line:
  `GLOBAL = fleet severity/freshness · SELECTED PROVIDER = provider status`
- evidence line:
  `UNKNOWN freshness = missing Runtime telemetry — inspect scrape target`

Increase Provenance and adjacent Status to `gridPos.h=4`; preserve provider
selection semantics and stable IDs.

## Acceptance criteria

- [ ] Body is `16px`; headline is `18px`.
- [ ] Global and selected-provider scopes are visually distinguishable.
- [ ] The full UNKNOWN freshness action is visible at 1366×768.
- [ ] Blank Provider still communicates `Selection required`.
- [ ] Dark/light and kiosk renders have no clipping or overflow.
- [ ] Terminal-state and repeat-geometry checks pass.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

