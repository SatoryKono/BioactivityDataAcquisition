# Dashboard Residual Layout issue pack (post-DRM)

**Status:** closed (2026-07-28, commit `e45e83b4a7`)  
**Wave code:** DRM-R  
**Date:** 2026-07-28  
**Implementation epic:** [#6853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6853)  
**Baseline SHA:** `e5d18d9c84` (post DRM #6844)

**Predecessors (closed):**
- [#6800](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6800) (DUX Phase-1)
- [#6828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6828) (DUX2 SSOT)
- [#6844](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6844) (DRM residual semantics)

**This wave is not** a re-open of DUX greenfield or a repeat of DRM-01…05 as-is.  
**This wave is** layout / first-screen contract completion and measurement after DRM semantic fixes.

## Context

DRM closed **semantic honesty** and **data seams**. Still open vs target first-screen contract:

- evidence often starts at y=7…11 (target y≤6)
- Trust four cards still at y=11
- shell ID/Processed / Triage compete on first paint
- Run Explorer grid overlaps; missing reconciliation/layers panels
- no-data taxonomy not fully typed
- layout tests still freeze coordinates/titles
- live 1600/1024 render evidence not packaged
- aggregate stage timeline / ordered stage_timings bars optional

## Key decisions (normative)

1. Keep 7 UIDs + full nav bus **0..6**
2. Do **not** merge Runtime and Run Explorer
3. Surgical `gridPos` / collapse / copy — not rewrite ~204 panels
4. No Prom `run_id`; no Loki/Tempo; ADR-010
5. Incident stays read-only; no write model
6. Measure proxies only; no causal MTTD/MTTI/MTTR

## Constraints (all children)

- Portfolio ≤7; stable UIDs/panel IDs where possible
- Tech-debt budgets must not increase
- Rollback unit = one phase/PR (restore JSON same UID)
- Change layout tests in the **same PR** as contract moves

## Issue matrix (published)

| Code | Issue | Pri | Phase | Title |
|------|-------|-----|-------|-------|
| DRM-R-00 | [#6853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6853) | P1 | meta | First-screen layout residual (post-DRM) |
| DRM-R-01 | [#6859](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6859) | P0 | R0 | Unfreeze layout tests + docs parity |
| DRM-R-02 | [#6856](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6856) | P1 | R1a | First-screen layout: Overview + Trust (y≤6) |
| DRM-R-03 | [#6855](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6855) | P1 | R1b | First-screen layout: Runtime + Provider + DQ |
| DRM-R-04 | [#6861](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6861) | P1 | R1c | Run Explorer grid fix + reconciliation/layers |
| DRM-R-05 | [#6860](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6860) | P1 | R2 | Typed no-data / UNKNOWN honesty |
| DRM-R-06 | [#6857](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6857) | P2 | R3 | Bounded visuals (optional) |
| DRM-R-07 | [#6858](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6858) | P1 | R4 | Measure, render evidence, release |
| DRM-R-08 | [#6854](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6854) | P3 | R5 | Deferred: incident write, Sankey, topology, portfolio shell |

## Delivery order

1. **PR-R0** [#6859](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6859) DRM-R-01  
2. **PR-R1a** [#6856](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6856) DRM-R-02  
3. **PR-R1b** [#6855](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6855) DRM-R-03  
4. **PR-R1c** [#6861](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6861) DRM-R-04  
5. **PR-R2** [#6860](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6860) DRM-R-05  
6. **PR-R3** [#6857](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6857) DRM-R-06 (optional)  
7. **PR-R4** [#6858](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6858) DRM-R-07  

## Rejected

- Repeat DRM semantic-only work as new epic
- Portfolio shrink / delete nav bus
- Persistent incident / Sankey / topology without ADR
- Greenfield monorepo dashboards

## Exit (epic)

- [ ] Children closed or deferred with dated rationale
- [ ] Evidence ≤ y=6 on primary boards (or documented exception)
- [ ] No Prom run_id; portfolio 7 UIDs; nav bus intact
- [ ] No-data states distinguishable on core panels
- [ ] Run Explorer: non-overlapping no-selection + selected-run + reconciliation
- [ ] S1–S6 post-test without critical regression; no MTTD claims
- [ ] Integration grafana/semantic gates green
