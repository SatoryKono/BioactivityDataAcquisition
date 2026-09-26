## Parent

_TBD_ (DSA-00)

## Problem

Audit counts ~**12 repeated ID / Processed Records** shell panels across the portfolio. Exact-run identity belongs on **Run Explorer** (+ Ops HTTP). Repeating it as first-screen KPI on fleet/domain boards burns fold space and confuses NOW vs selected-run semantics.

## Scope

- [ ] Inventory all ID / Processed Records / exact-run shell panels on 7 UIDs
- [ ] Keep **one hub** on `bioetl-run-explorer-v1` (+ Trust forensic below fold if required for resume safety)
- [ ] Replace other first-screen copies with compact handoff links (time + vars preserved)
- [ ] Do not put `run_id` into Prometheus selectors
- [ ] Update navigation-links / first-screen contracts if titles move

## Out of scope

- Changing Ops HTTP schemas
- Scenes-only implementation without JSON SOT update

## Acceptance

- [ ] First-screen ID/Processed KPI appears on ≤1 primary board (Run Explorer) as full block
- [ ] Other boards: link or collapsed forensic only
- [ ] No Prom `run_id` labels introduced
- [ ] Integration tests/docs updated

## Files

- `grafana/dashboards/*.json`
- `docs/03-guides/dashboards/contracts/navigation-links.yaml` (if present)
- `tests/integration/test_grafana_*.py`
