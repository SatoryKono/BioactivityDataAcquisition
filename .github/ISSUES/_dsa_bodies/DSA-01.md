## Parent

_TBD_ (DSA-00)

## Problem

Deep audit **Contract Repair Gate**: canonical inventory does not match shipped dashboards. Redesign without a green inventory migrates an unstable specification.

Observed mismatch classes (audit + local panel snapshot):

| uid | visual panels (shipped) | Contract risk |
| --- | ---: | --- |
| `bioetl-control-plane-v1` | 52 | title/count drift |
| `bioetl-overview-v2` | 21 | subsystem tables vs inventory |
| `bioetl-runtime` | 36 | panel 9102/9105 titles/types |
| `bioetl-provider-health-v2` | 28 | selector registry |
| `bioetl-dq-v2` | 33 | 9101/9102 titles |
| `bioetl-incident-v1` | 11 | datasource: Ops HTTP vs expected |
| `bioetl-run-explorer-v1` | 12 | datasource/selector UID rows |

## Scope

- [ ] Reconcile `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml` to shipped JSON
- [ ] Fix panel counts, titles, datasources, selector registry rows
- [ ] Regenerate inventory/guide surfaces used by CI/docs
- [ ] Ensure inventory check covers all 7 provisioned UIDs
- [ ] Document any intentional exceptions with dated rationale

## Out of scope

- Visual redesign / panel deletion (DSA-02+)
- Scenes app code changes
- Recording-rule invents

## Acceptance

- [ ] Inventory QA PASS against `grafana/dashboards/*.json`
- [ ] Datasource contracts for Incident + Run Explorer match Ops HTTP reality
- [ ] Related integration/config tests green
- [ ] Docs inventory mirrors regenerated if generated

## Files

- `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`
- `docs/03-guides/dashboards/dashboard-inventory.md` (if generated/hand-synced)
- `grafana/dashboards/*.json` (titles only if required for SSOT; prefer contract fix)
- inventory-related tests under `tests/integration/test_grafana_*.py`

## Priority

P0 — blocks trustworthy A1 redesign.
