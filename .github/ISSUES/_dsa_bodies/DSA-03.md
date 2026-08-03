## Parent

_TBD_ (DSA-00)

## Problem

Deep audit: giant cards for `OK` / `SCRAPING` / `0` / `UNKNOWN` share the same visual weight while encoding different claim types. Operators must remember hidden rules (“do not treat these badges as peers”).

Target first-screen cell contract:

`state × confidence × basis × next_action`

Empty-state taxonomy already partially documented (`VALID_EMPTY`, `UNKNOWN`/`TELEMETRY_ABSENT`, `INCOMPLETE`) but not consistently applied as peer-safe encoding.

## Scope

- [ ] Codify first-screen cell grammar in operator UX / verdict ontology (if gaps)
- [ ] Audit primary boards: no silent green zero without expectedness/freshness
- [ ] Telemetry collection state (e.g. SCRAPING) is a **confidence chip**, not a peer health KPI
- [ ] Color is accent only; status always has text/icon
- [ ] Add/extend coded checks where feasible (titles, mappings, no bare severity numbers)

## Out of scope

- New Prometheus series
- Full visual redesign of every panel
- WCAG full site audit (spot-check contrast only)

## Acceptance

- [ ] Documented grammar applied on Trust, Overview, Runtime, Provider, DQ, Incident first screens
- [ ] No bare numeric severity as sole status
- [ ] UNKNOWN always exposes reason/basis path
- [ ] Related grafana semantic/layout tests green

## Files

- `docs/03-guides/dashboards/verdict-ontology.md`
- `docs/03-guides/dashboards/operator-ux-v2.md`
- `grafana/dashboards/*.json` (surgical mapping/overrides)
- `tests/integration/test_grafana_*.py`

## Priority

P1 — cross-cutting; can land with board PRs but needs explicit owner.
