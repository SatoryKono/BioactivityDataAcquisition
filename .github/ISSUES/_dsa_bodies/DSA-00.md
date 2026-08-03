## Summary

Execute **Dashboard System 2.0 Deep Audit residual (wave DSA)** after closed DS2/DSS: repair contract SSOT drift, compress first-screen decision surfaces toward the audit’s six task workspaces, remeasure usability proxies — **without** deleting stable UIDs or reopening greenfield Unified Plan scope.

## Why now

DS2 fixed P0 truth/render defects and shipped compression slices; DSS scaffolded optional Scenes routes (ADR-053). The deep audit (2026-07-28) still finds:

- **193 visual panels** with ~75% stat/table/text surface
- four mixed semantics (system state / telemetry trust / historical evidence / exact-run accounting)
- inventory contract drift vs shipped JSON
- repeated shell ID/Processed Records and giant peer cards that force mental merge

## Waves

| Wave | Scope | Exit |
| --- | --- | --- |
| **A0** | Contract Repair Gate (DSA-01) | inventory/selectors/datasources PASS |
| **A1** | Workspace first-screen residuals (DSA-02…08) | ≤5 decision objects; clear handoffs; no metric invention |
| **A2** | Parity ledger + usability proxies (DSA-09) | ledger complete; baseline updated |
| **Track** | Viz + cutover (DSA-10…11) | gates only until ADR/data ready |

## Accepted decisions

1. Keep **7 UIDs**; logical IA = 6 workspaces (Trust+DQ tabs only)
2. Surgical JSON SOT edits; no second monorepo dashboard tree
3. Incident stays **read-only**
4. Node graph / Sankey / waterfall only contract-gated
5. Proxies only — no MTT* claims

## Constraints

- ADR-010 optional Grafana
- No invent metrics; no Prom `run_id`
- Tech-debt budgets must not increase
- Portfolio ≤7

## Children

See `.github/ISSUES/DSA-2026-07-28-DASHBOARD-DEEP-AUDIT-RESIDUAL-ISSUE-PACK.md` (numbers filled after publish).

## Predecessors

- #6901 DS2 epic (closed)
- #6911 ADR-053 (closed)
- #6915 DSS epic (closed)
- #6800 DUX / #6844 DRM / #6853 DRM-R

## UX grammar

`state → impact → evidence confidence/age → location/cause → safe action → verification`

## Source

Deep audit HTML: `BioETL_Dashboard_System_2.0_Deep_Audit_and_Redesign_2026-07-28.html` (2026-07-28).
