## Parent

_TBD_ (DSA-00)

## Problem

Run Explorer (`bioetl-run-explorer-v1`) is the correct exact-run boundary, but first screen still weak:

- Empty selection shows empty ID panels instead of recent-runs/search utility
- Selected-run narrative order does not match investigation: identity → accounting → verdict/reasons → timings → artifacts
- Long IDs hard to scan; deep links from other boards must remain stable

## Scope

- [ ] **No-selection state**: recent runs / search utility, not empty identity cards
- [ ] **Selected state**: header → identity/lineage → accounting → reasons → timings → artifacts
- [ ] Visual shorten long IDs with copy-friendly full value in tooltip/field
- [ ] Ensure inbound data links from Operations/Incident/Trust/DQ preserve time + vars
- [ ] Ops HTTP only for exact-run; no Prom `run_id`

## Out of scope

- Merging Run Explorer with Runtime
- New artifact storage backends

## Acceptance

- [ ] Empty selection is useful within 30s
- [ ] Selected run answers accounting + reasons without random scroll
- [ ] No Prom `run_id` labels
- [ ] Run Explorer integration tests green

## Files

- `grafana/dashboards/bioetl-run-explorer-v1.json`
- `docs/03-guides/dashboards/panels/*run-explorer*`
- `tests/integration/test_grafana_*.py`
