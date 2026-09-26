## Parent

_TBD_ (DSA-00)

## Problem

A1 compression will remove/collapse panels. Without a **query parity ledger**, functional Prom/HTTP evidence can be silently lost. Usability proxies from DUX2/DS2 need remeasure after residual work (not MTT* claims).

## Scope

- [ ] Maintain ledger: each removed/collapsed panel → destination panel/board + query refs
- [ ] Verify no functional Prom/HTTP loss for primary investigation paths
- [ ] Re-run usability proxy protocol into `reports/observability/usability-baseline.md`
- [ ] Targets (proxies only): clicks to cause 3–5; screens 2–3; first suspect ≤30s; portfolio ≤7
- [ ] Explicitly **do not** claim MTTD/MTTI/MTTR without production instrumentation

## Out of scope

- Live operator A/B study at scale
- Scenes parity (covered under ADR-053 / DSS unless regressions found)

## Acceptance

- [ ] Query parity ledger complete for A1 changes
- [ ] Usability baseline updated with date + method
- [ ] No invented series; portfolio still 7 UIDs

## Files

- `reports/observability/usability-baseline.md`
- `docs/03-guides/dashboards/usability-baseline-protocol.md`
- ledger path (repo-chosen under `reports/observability/` or docs contracts)
- tests only if ledger is machine-checked

## Depends on

- DSA-02…08 substantially complete
