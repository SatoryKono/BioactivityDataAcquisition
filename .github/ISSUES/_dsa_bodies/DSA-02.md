## Parent

_TBD_ (DSA-00)

## Problem

Overview (`bioetl-overview-v2`) still behaves as a **status inventory**, not Operations Home:

- Status UNKNOWN while Runtime/Control Plane OK and DQ/Provider UNKNOWN — no composite explanation
- Multiple subsystem status tables require mental merge
- Three state timelines with low localization value
- Silver Rejects / rate peer KPIs conflict with DQ UNKNOWN and exact-run accounting
- Diagnostics navigation shows raw metric names; ID/Processed Records repeat

Audit target: **Operations Home** — detection, fleet verdict, ranked suspects, first handoff.

## Scope

- [ ] One **composite fleet verdict** (state × confidence × basis)
- [ ] Collapse subsystem status tables into **one domain matrix** (pipeline × domain or equivalent)
- [ ] Replace/compress three state bands → aligned small multiples or event stream
- [ ] First Action → ranked next-best-action (≤4), not prose wall
- [ ] Move Silver Rejects KPI to Data Trust handoff (not peer fleet KPI)
- [ ] Keep portfolio nav bus 0–6; prefer task labels over raw metric names
- [ ] Update first-screen / overview integration contracts in the same PR

## Out of scope

- Deleting Overview UID
- Incident write model
- Topology map

## Acceptance

- [ ] Operator can answer “what needs attention now?” in ≤30s without expanding rows
- [ ] First-screen decision objects ≤5
- [ ] Context-preserving links to Incident / domain boards with time range
- [ ] Integration overview/first-screen tests green
- [ ] Panel docs synced

## Files

- `grafana/dashboards/bioetl-overview-v2.json`
- `docs/03-guides/dashboards/panels/bioetl-overview-v2-panels.md` (if present)
- `docs/03-guides/dashboards/operator-ux-v2.md`
- `tests/integration/test_grafana_*.py` (overview / first-screen)

## Depends on

- DSA-01 Contract Repair preferred first
