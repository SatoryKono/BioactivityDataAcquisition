# Dashboard Residual Migration issue pack (post-audit)

**Status:** published  
**Wave code:** DRM  
**Date:** 2026-07-28  
**Predecessors (closed):**
- #6800 (DUX Phase-1 foundation)
- #6828 (DUX2 Phase-2 residual SSOT — closed; execution refined here)

**This wave is not** a re-open of greenfield Unified Plan / DUX rewrite.  
**This wave is** residual migration of **already shipped** 7-board portfolio.

## Key decisions (normative)

1. **Keep portfolio (7 UIDs):**
   - `bioetl-control-plane-v1`, `bioetl-overview-v2`, `bioetl-runtime`
   - `bioetl-provider-health-v2`, `bioetl-dq-v2`
   - `bioetl-incident-v1`, `bioetl-run-explorer-v1`
2. **Keep full nav bus 0..6** and target-scoped handoff vars.
3. **Do not merge** Pipeline Diagnostics (Runtime) and Run Explorer (different time grains).
4. Fix **first-screen hierarchy/semantics**, not rewrite all ~204 panel objects.
5. Use existing **recording rules + Ops HTTP**; no `run_id` in Prometheus; no Loki/Tempo return.
6. Incident = **honest read-only triage**; persistent working record → separate ADR (out of scope).
7. **Measure** usability before/after; MTTD/MTTI/MTTR only after incident telemetry exists.

## Implementation gaps (from audit)

| Gap | Action owner issue |
|-----|-------------------|
| Missing `reports/observability/usability-baseline.md` | DRM-01 |
| UX-report freshness test fixed date / clean-tree skip | DRM-01 |
| Docs dual-describe 7-board vs old 5/8 bus | DRM-01 |
| `dashboard-inventory.yaml` header still 5-dashboard | DRM-01 |
| Incident Ranked Suspects = union topk, not ranking | DRM-04 |
| Incident Alert Timeline is instant, not range | DRM-04 |
| DQ recording `action_target=silver_reject_explorer` retired | DRM-04 |
| Runtime trust healthy=0 as SCRAPING jargon | DRM-03 |
| Run Explorer ignores pipeline-run-report endpoints | DRM-05 |
| Persistent incident record impossible (no write API) | DRM-08 deferred |

## Constraints (all children)

- ADR-010 local-only; Grafana optional
- Portfolio ≤7; stable UIDs
- No invent metrics; no Prom `run_id` labels
- No reintroduce Loki/Tempo/Silver Reject UI without ADR
- Tech-debt budgets must not increase
- Surgical JSON edits; preserve panel IDs where possible
- Rollback unit = one phase/PR

## Issue matrix

| Code | Pri | Phase | Title |
|------|-----|-------|-------|
| DRM-00 | P1 | meta | Residual dashboard UX migration (post-DUX2 audit) |
| DRM-01 | P0 | 2.0 | Re-baseline, gate repair, docs/contracts parity |
| DRM-02 | P1 | 2.1a | First-screen: Overview + Trust |
| DRM-03 | P1 | 2.1b | First-screen: Runtime + Provider + DQ |
| DRM-04 | P1 | 2.2 | Incident semantic correction (read-only) |
| DRM-05 | P1 | 2.3 | Run Explorer depth via pipeline_run_report_v1 |
| DRM-06 | P2 | 2.4 | Bounded visual upgrades (optional) |
| DRM-07 | P1 | 2.5 | Measure, gates, render evidence, release |
| DRM-08 | P3 | deferred | Gated: persistent incident, Sankey, topology, portfolio shrink |

## Delivery order (PRs)

1. **PR-A** DRM-01  
2. **PR-B** DRM-02  
3. **PR-C** DRM-03  
4. **PR-D** DRM-04  
5. **PR-E** DRM-05  
6. **PR-F** DRM-06 (optional)  
7. **PR-G** DRM-07  

Parallel after PR-A: lane1 Overview/Trust/Runtime; lane2 Incident+Run Explorer; shared nav/no-data review.

## Rejected in this wave

- Shrink portfolio to 6
- Delete navigation bus
- Persistent incident write model
- True waterfall / Sankey / dependency graph without new contracts
- Greenfield monorepo `bioetl-dashboards/`

## Evidence anchors

- Snapshot: `f2a8a0b1341de55b206f62654bd1089b533a4275` (audit-referenced)
- JSON: `grafana/dashboards/*.json`
- Rules: `grafana/prometheus-rules/bioetl_observability.yml`
- Contracts: `operator-ux-v2.md`, `verdict-ontology.md`, `migration-map-v2.md`, `contracts/*`
- Ops: `/ops/control-plane/*`, `/ops/observability/*`, `pipeline_run_report_v1`
