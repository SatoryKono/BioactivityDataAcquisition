## Parent

_TBD_ (DSA-00)

## Problem

Incident Workspace (`bioetl-incident-v1`) remains read-only triage (correct under ADR constraints) but still fragments evidence:

- Current Alerts and Alert State History are one temporal chain, often split
- Impact/confidence still partly prose
- Multiple suspect surfaces may reappear after partial DS2 compression
- No working incident record (owner/ack) — **must stay out of scope** without backend ADR

Audit target for this residual: **evidence timeline + ranked hypotheses + decision rail** (read-only).

## Scope

- [ ] Unify alerts now + history into one **evidence timeline** narrative (layout/links/ordering)
- [ ] Keep single ranked suspects matrix as primary (no reintroduction of 4 peer suspect tables)
- [ ] Structured impact/confidence fields (not only markdown)
- [ ] Decision rail ≤4 next actions; resume → Trust Primary recovery; identity → Run Explorer
- [ ] Preserve Status map-or-requery (no bare numbers; DS2-02 invariant)
- [ ] Table severity color only on severity field

## Out of scope

- Persistent incident store / owner / acknowledge write-path
- External paging integrations
- MTT* measurement claims

## Acceptance

- [ ] Operator can classify “real incident vs telemetry blindness” without reading multi-page prose
- [ ] Read-only invariant documented and tested
- [ ] Incident grafana tests green

## Files

- `grafana/dashboards/bioetl-incident-v1.json`
- `docs/03-guides/dashboards/panels/bioetl-incident-v1-panels.md`
- `tests/integration/test_grafana_*.py`
