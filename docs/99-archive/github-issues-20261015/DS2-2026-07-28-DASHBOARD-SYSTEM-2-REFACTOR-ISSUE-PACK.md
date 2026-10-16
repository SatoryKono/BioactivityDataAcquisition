# Dashboard System 2.0 refactor issue pack (post DRM/DRM‑R audit)

**Status:** published  
**Wave code:** DS2  
**Date:** 2026-07-28  
**Implementation epic:** [#6901](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6901)  
**Baseline SHA:** `9e7e6b8ed577a32de314cb6fc2b9ff0bc46a25f3` (local `main` at pack authoring)

**Predecessors:**
- [#6800](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6800) (DUX Phase-1)
- [#6828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6828) (DUX2 residual SSOT)
- [#6844](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6844) (DRM residual semantics)
- [#6853](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6853) (DRM‑R first-screen layout residual)

**This wave is not** a greenfield Unified Plan rewrite or a re-open of DRM/DRM‑R as-is.  
**This wave is** post-audit execution: **P0 truth/render repair → JSON compression/routing → optional Scenes shell**, preserving DRM/DRM‑R semantic gains.

## Context

DRM/DRM‑R shipped important honesty fixes (VALID_EMPTY, NOW/RUN/RANGE, fleet-first Provider Health, domain suspects, exact-run Run Explorer). A follow-up code/render audit still found three **P0 blockers** before radical redesign:

1. **Pipeline Diagnostics** `#9105` *Monitor Aggregate Stage Lag Timeline* — `state-timeline` on continuous `bioetl_stage_lag_seconds` → live *Data does not have a time field*.
2. **Incident** Status bare red `3` (unmapped) + table-wide `color-background` paints Time/alertname/pipeline as severity.
3. **Trust** shipped `#906` title **Primary recovery**, while selected integration contracts still expect *Next Action: Replay Diagnostics* (suite red).

North Star (later waves): optional Grafana App Plugin + Scenes with six task/object workspaces; **seven stable UIDs remain** provisioned fallbacks until parity/usage gate.

## Accepted decisions (normative)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Trust `#906` title | Keep **Primary recovery**; sync tests/scripts/docs to that SSOT |
| 2 | Incident Status `3` | **map-or-requery with label** — no bare number; map or requery + reason |
| 3 | Runtime stage lag | **A — timeseries** continuous lag by stage (not state-timeline without frame contract) |
| 4 | Scenes shell | **ADR after Wave 0 green; build after Wave 1** |

UX grammar: **state → impact → evidence confidence/age → location/cause → safe action → verification**. Color is secondary; UNKNOWN always has reason; selectors only where they change visible evidence; links carry object/time/basis/origin.

## Constraints (all children)

- Portfolio **≤7** first-class boards; stable UIDs; do not delete Trust/DQ UIDs in this wave
- SOT: `grafana/dashboards/*.json` until Wave 2 app routes are proven
- ADR-010: Grafana optional; no required Docker/Redis; app shell ≠ control plane
- **No** invent metrics; **no** `run_id` Prometheus labels
- **No** Loki/Tempo/Silver Reject UI without ADR
- Tech-debt budgets **must not increase**
- Incident remains **read-only** until Wave 4 ADR + backend
- Measure usability **proxies** only; no causal MTTD/MTTI/MTTR claims without production telemetry
- Surgical JSON edits; preserve panel IDs where possible; rollback unit = one PR/issue

## Portfolio (fixed)

| # | uid | Role |
| ---: | --- | --- |
| 0 | `bioetl-control-plane-v1` | Trust / resume safety |
| 1 | `bioetl-overview-v2` | Fleet / Operations Home alias |
| 2 | `bioetl-runtime` | Pipeline Flow |
| 3 | `bioetl-provider-health-v2` | Dependency Health |
| 4 | `bioetl-dq-v2` | Data trust (Now/Run/Range) |
| 5 | `bioetl-incident-v1` | Incident Console |
| 6 | `bioetl-run-explorer-v1` | Run Explorer |

Target IA merge of Trust+DQ is **tabs only** in Wave 2+; physical UID retirement is Wave 5 only.

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DS2-00 | [#6901](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6901) | meta | epic | Dashboard System 2.0 refactor (post DRM/DRM‑R) |
| DS2-01 | [#6902](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6902) | P0 | W0 | Runtime `#9105` stage lag → timeseries frame fix |
| DS2-02 | [#6903](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6903) | P0 | W0 | Incident Status map-or-requery + table color overrides |
| DS2-03 | [#6904](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6904) | P0 | W0 | Trust `#906` Primary recovery contract SSOT |
| DS2-04 | [#6905](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6905) | P0 | W0 | Grafana cross-cutting gates (frame/enum/table color/render) |
| DS2-05 | [#6906](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6906) | P1 | W1 | Incident single ranked suspect matrix + row links |
| DS2-06 | [#6907](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6907) | P1 | W1 | Runtime escalation matrix / peer-stat compression |
| DS2-07 | [#6908](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6908) | P1 | W1 | Trust gate matrix + DQ accounting strip |
| DS2-08 | [#6909](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6909) | P1 | W1 | Provider fleet matrix + Run Explorer browse/selected |
| DS2-09 | [#6910](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6910) | P1 | W1 | Selector applicability + nav/data-link contracts + usability remeasure |
| DS2-10 | [#6911](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6911) | P2 | W2 | ADR: optional Grafana Scenes app shell (after W0 green) |
| DS2-11 | [#6912](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6912) | P2 | W2 | Scenes app shell proof + JSON parity (after W1 + ADR) |
| DS2-12 | [#6913](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6913) | P3 | W3 | Domain visualization upgrade (contract-gated) |
| DS2-13 | [#6914](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6914) | P3 | W4–5 | ADR-gated capabilities + measured cutover tracking |

## Delivery order

1. **PR-0a** DS2-01 Runtime lag timeseries  
2. **PR-0b** DS2-02 Incident status + table color  
3. **PR-0c** DS2-03 Trust Primary recovery SSOT  
4. **PR-0d** DS2-04 Cross-cutting gates (may land with 0a–0c or immediately after)  
5. **Wave 0 exit** — selected integration suite green; zero primary render errors  
6. **PR-1a…1e** DS2-05 → DS2-09 (Wave 1; parallelizable after W0)  
7. **ADR** DS2-10 (after W0 green; may draft earlier, merge after W0)  
8. **Build** DS2-11 only after Wave 1 green + accepted ADR  
9. **Tracking** DS2-12 / DS2-13 — no unsolicited implementation  

## Wave exit criteria

### Wave 0
- [ ] Selected suite green (`test_grafana_config`, first-screen, metric-semantics, layout/metadata, overview, pipeline_runtime)
- [ ] Zero primary-panel render errors (no broken stage-lag frame)
- [ ] No bare status numbers; no table-wide severity paint
- [ ] Trust next-action title SSOT = **Primary recovery** across JSON/tests/scripts/docs

### Wave 1
- [ ] First-screen decision objects ≤5 on primary boards (coded audit)
- [ ] Row-specific context-preserving links; no generic link bus as only path
- [ ] Usability proxies re-measured in `reports/observability/usability-baseline.md` (no MTT* claims)
- [ ] Query parity ledger: no functional Prom/HTTP loss

### Wave 2+
- [ ] ADR accepted before Scenes code
- [ ] JSON fallback remains operational for all 7 UIDs
- [ ] Parity tests JSON vs app routes
- [ ] UID retirement only after usage + parity gate (Wave 5)

## Rejected in this wave

- Immediate portfolio shrink / delete Trust or DQ UID
- Merge Runtime + Run Explorer
- One mega-dashboard
- Topology / Sankey / waterfall / persistent incident without ADR + data contract
- Aggressive green/red without text labels
- Causal MTTD/MTTI/MTTR claims without production instrumentation

## Evidence anchors

- Shipped JSON: `grafana/dashboards/*.json`
- Rules: `grafana/prometheus-rules/bioetl_observability.yml`
- Contracts: `docs/03-guides/dashboards/operator-ux-v2.md`, `verdict-ontology.md`, `design-system.md`, `dashboard-system-2.0-phase2-residual.md`
- Residual scripts: `scripts/ops/observability/grafana/apply_dux2_residual.py`, `render_nav_bus.py`
- Integration tests: `tests/integration/test_grafana_*.py`, `test_pipeline_runtime_dashboard.py`
- Prior packs: `DRM-2026-07-28-*.md`, `DRMR-2026-07-28-*.md`, `DUX2-2026-07-28-*.md`

## Publish record

- `reports/quality/ds2-2026-07-28-issue-publish.json` (filled after `gh issue create`)
