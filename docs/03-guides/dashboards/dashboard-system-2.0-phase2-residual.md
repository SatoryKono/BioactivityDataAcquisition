______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Dashboard System 2.0 — Phase-2 Residual

**Epic:** [#6828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6828)  
**Builds on:** closed epic [#6800](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6800) (DUX Phase-1)  
**Pack:** `.github/ISSUES/DUX2-2026-07-28-DASHBOARD-SYSTEM-2-PHASE2-RESIDUAL-ISSUE-PACK.md`

## Status of external “Unified Plan v2.0”

The greenfield Unified Plan (Tier0–3 sprawl, Loki/Tempo explorers, Sankey/Topology/Health Score, 6 weeks × 5 FTE) is **not an execution plan** for this repository. It conflicts with:

- ADR-010 (Grafana optional / local-only default)
- Monitoring surface reduction 2026-07-23 (Loki/Tempo/Silver Reject UI removed)
- Portfolio cap **≤7** first-class boards
- No invented Prometheus series / no `run_id` Prom labels
- Work already shipped in DUX Phase-1

Use Unified Plan only as **benchmark inspiration**, not as delivery scope.

## Fixed portfolio

| # | uid | Role |
| ---: | --- | --- |
| 0 | `bioetl-control-plane-v1` | Trust / resume safety |
| 1 | `bioetl-overview-v2` | Fleet / Global Ops **alias** (not a new board) |
| 2 | `bioetl-runtime` | Pipeline explorer |
| 3 | `bioetl-provider-health-v2` | Provider fleet |
| 4 | `bioetl-dq-v2` | Data trust (Now/Run/Range) |
| 5 | `bioetl-incident-v1` | Incident workspace |
| 6 | `bioetl-run-explorer-v1` | Run identity explorer |

## Phase-2 residual goals

1. Stronger visual encoding of **existing** status series (no new metrics).
2. Deeper Incident suspects + typed empty states.
3. Deeper Run Explorer via **HTTP Ops only**.
4. Standard First Action / empty-state chrome.
5. Nav readability polish via `render_nav_bus.py`.
6. Re-measure usability **proxies** (not MTT* claims).

## Non-goals

- Portfolio >7 or parallel monorepo dashboard tree
- Reintroduce Loki/Tempo/Silver Reject UI without ADR
- System Health Score / ML DDx / Sankey / Topology without metrics+ADR gate
- Global 5–10s refresh
- Tech-debt budget increases

## Children (GitHub)

| ID | Issue | Priority |
| --- | --- | --- |
| DUX2-01 | #6831 SSOT + rebaseline | P0 |
| DUX2-02 | #6829 Visualization | P1 |
| DUX2-03 | #6834 Incident depth | P1 |
| DUX2-04 | #6832 Run depth | P2 |
| DUX2-05 | #6835 CTA/empty chrome | P1 |
| DUX2-06 | #6836 Nav polish | P2 |
| DUX2-07 | #6837 Usability re-measure | P1 |
| DUX2-08 | #6833 Docs sync | P2 |
| DUX2-09 | #6830 Gated backlog | P3 tracking |

## Success proxies (targets, not claims)

| Proxy | Target |
| --- | ---: |
| Time-to-first-suspect (S1) | ≤30s |
| Clicks to cause | 3–5 |
| Screens / investigation | 2–3 |
| Portfolio size | ≤7 |
| Invented series | 0 |

See `usability-baseline-protocol.md` and `reports/observability/usability-baseline.md`.


## DS2 follow-on (2026-07-28)

Post-DRM-R audit execution: epic [#6901](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6901).
Wave 0 truth/render + Wave 1 compression ship on JSON; optional Scenes shell is
[ADR-053](../../02-architecture/decisions/ADR-053-optional-grafana-scenes-app-shell.md).
Issue pack: `.github/ISSUES/DS2-2026-07-28-DASHBOARD-SYSTEM-2-REFACTOR-ISSUE-PACK.md`.

## DSA deep-audit residual (2026-07-28) — closed

Post DS2/DSS closeout residual from the deep UX audit HTML:
epic [#6982](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6982) (closed with children #6983–#6993).
Shipped: Contract Repair inventory/selectors SSOT; first-screen residual narrative on
7 JSON boards; query parity ledger + usability remeasure. Viz/cutover remain deferred.
Issue pack: `.github/ISSUES/DSA-2026-07-28-DASHBOARD-DEEP-AUDIT-RESIDUAL-ISSUE-PACK.md`.
Publish record: `reports/quality/dsa-2026-07-28-issue-publish.json`.
Ledger: `reports/observability/query-parity-ledger-dsa-2026-07-28.md`.
