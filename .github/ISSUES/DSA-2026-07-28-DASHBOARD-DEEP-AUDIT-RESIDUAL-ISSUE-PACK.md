# Dashboard System 2.0 — Deep Audit residual issue pack

**Status:** publishing  
**Wave code:** DSA  
**Date:** 2026-07-28  
**Source audit:** `BioETL_Dashboard_System_2.0_Deep_Audit_and_Redesign_2026-07-28.html`  
**Baseline SHA:** `2ba9ae3259` (local `main` at pack authoring)

**Predecessors (closed):**
- [#6901](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6901) DS2 refactor (W0–W1 truth + compression)
- [#6911](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6911) ADR-053 Scenes shell
- [#6915](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6915) DSS Scenes scaffold / dual-path docs
- [#6800](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6800) DUX Phase-1
- [#6844](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6844) DRM residual semantics
- [#6853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6853) DRM-R layout residual

## Context

DS2/DSS closed P0 truth/render blockers, JSON compression slices, ADR-053, and a Scenes scaffold.
A follow-up **deep UX audit** (2026-07-28) still finds the portfolio optimized for **metric completeness**, not a bounded number of operator decisions:

- **193 visual panels** (61 stat + 51 table + 33 text ≈ 75% surface)
- four semantics mixed at one visual level: system state / telemetry trust / historical evidence / exact-run accounting
- Contract inventory drift vs shipped JSON (counts, titles, datasources, selectors)
- repeated ID/Processed Records shell; giant peer cards; empty trends as first-screen noise

This wave is **not** a greenfield Unified Plan, not a re-open of DS2-01…09 as-is, and not immediate UID retirement.
This wave is **post-closeout residual**: contract repair → first-screen decision compression per workspace → parity/usability → tracking gates for viz/cutover.

## Accepted decisions (normative)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Portfolio | Keep **7 stable UIDs**; logical IA = 6 task workspaces (Trust+DQ tabs only in Scenes/IA) |
| 2 | Migration | Surgical JSON edits on SOT `grafana/dashboards/*.json`; no second monorepo tree |
| 3 | Shadow | Shadow folder / Scenes dual-path only where ADR-053 already allows; not a Wave-0 rewrite |
| 4 | Incident | Remains **read-only** (no owner/ack write-path without ADR + backend) |
| 5 | Viz | Node graph / Sankey / waterfall only **contract-gated** (DSA-10); no invent metrics |
| 6 | Measurement | Usability **proxies** only; no causal MTTD/MTTI/MTTR claims |

UX grammar: **state → impact → confidence/age → location/cause → safe action → verification**.

## Constraints (all children)

- Portfolio ≤7; do not delete Trust/DQ UIDs in this wave
- ADR-010: Grafana optional; no required Docker/Redis
- No invent metrics; no `run_id` Prometheus labels
- No Loki/Tempo/Silver Reject UI without ADR
- Tech-debt budgets must not increase
- Color secondary; UNKNOWN always has reason; green only with expectedness
- Rollback unit = one PR/issue; preserve panel IDs where possible

## Portfolio (fixed UIDs / logical roles)

| # | uid | Logical role (audit) |
| ---: | --- | --- |
| 0 | `bioetl-control-plane-v1` | Data Trust & Recovery (safety gate tab) |
| 1 | `bioetl-overview-v2` | Operations Home |
| 2 | `bioetl-runtime` | Pipeline Flow |
| 3 | `bioetl-provider-health-v2` | Dependency Health |
| 4 | `bioetl-dq-v2` | Data Trust & Recovery (delivery/accounting tab) |
| 5 | `bioetl-incident-v1` | Incident Console (read-only) |
| 6 | `bioetl-run-explorer-v1` | Run Explorer (exact-run hub) |

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DSA-00 | _TBD_ | meta | epic | Deep-audit residual refactor (post DS2/DSS) |
| DSA-01 | _TBD_ | P0 | A0 | Contract Repair Gate — inventory/selectors/datasources SSOT |
| DSA-02 | _TBD_ | P1 | A1 | Operations Home — composite verdict + domain status matrix |
| DSA-03 | _TBD_ | P1 | A1 | First-screen verdict grammar (state×confidence×basis×action) |
| DSA-04 | _TBD_ | P1 | A1 | Deduplicate ID/Processed Records shell → Run Explorer hub |
| DSA-05 | _TBD_ | P1 | A1 | Pipeline Flow residual — telemetry chip + blockers + handoffs |
| DSA-06 | _TBD_ | P1 | A1 | Dependency Health residual — freshness-aware fleet matrix |
| DSA-07 | _TBD_ | P1 | A1 | Incident evidence timeline (alerts now + history chain) |
| DSA-08 | _TBD_ | P1 | A1 | Run Explorer first-screen narrative (empty/selected) |
| DSA-09 | _TBD_ | P2 | A2 | Query parity ledger + usability proxy remeasure |
| DSA-10 | _TBD_ | P3 | track | Domain visualization upgrade (contract-gated tracking) |
| DSA-11 | _TBD_ | P3 | track | Measured cutover / UID retirement tracking |

## Delivery order

1. **PR-A0** DSA-01 Contract Repair (blocks trustworthy redesign)
2. **PR-A1a…A1g** DSA-02…08 (parallelizable after A0; one board-family per PR preferred)
3. **PR-A2** DSA-09 parity + usability remeasure
4. **Tracking** DSA-10 / DSA-11 — no unsolicited implementation

## Wave exit criteria

### A0
- [ ] `dashboard-inventory.yaml` matches shipped JSON (counts/titles/datasources/selectors)
- [ ] Generated inventory/guide surfaces regenerated
- [ ] Inventory CI/check PASS on 7 UIDs

### A1
- [ ] Primary boards: first-screen decision objects ≤5 (coded audit)
- [ ] No giant peer cards for telemetry collection state vs pipeline health
- [ ] ID/Processed Records not repeated as first-screen KPI on ≥3 boards
- [ ] Context-preserving row/domain handoffs retained
- [ ] Incident remains read-only

### A2
- [ ] Query parity ledger complete for panels removed/collapsed
- [ ] `reports/observability/usability-baseline.md` updated (proxies only)

### Track
- [ ] Viz/cutover items only advance when data contract + ADR gates open

## Rejected in this wave

- Immediate portfolio shrink / delete Trust or DQ UID
- Merge Runtime + Run Explorer into one board
- One mega-dashboard
- Topology / Sankey / persistent incident write without ADR + data contract
- Causal MTT* as release KPI
- Greenfield shadow monorepo replacing SOT JSON

## Evidence anchors

- Audit HTML (local): `BioETL_Dashboard_System_2.0_Deep_Audit_and_Redesign_2026-07-28.html`
- SOT JSON: `grafana/dashboards/*.json`
- Contracts: `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`
- Operator UX: `docs/03-guides/dashboards/operator-ux-v2.md`, `verdict-ontology.md`
- ADR-053: `docs/02-architecture/decisions/ADR-053-optional-grafana-scenes-app-shell.md`
- Prior packs: `DS2-2026-07-28-*.md`, `DSS` publish record
- Tests: `tests/integration/test_grafana_*.py`, `test_pipeline_runtime_dashboard.py`

## Publish record

- `reports/quality/dsa-2026-07-28-issue-publish.json`
