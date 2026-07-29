# Dashboard visual enforcement residual — DUX4

**Status:** closed (implementation landed 2026-07-29; issues #7088–#7115)
**Wave code:** DUX4
**Date:** 2026-07-29
**Source audit:** `BIOETL-GRAFANA-UX-AUDIT-20260729-085334` (full report; 7 boards / ~152–193 visual panels)
**Predecessor wave:** DUX3 epic #7053 (closed #7054–#7077) — contracts + description grammar + shell collapse
**Baseline:** post-DUX3 working tree / local `main`

## Context

DUX3 closed **contract-level** residual after the 2026-07-29 screenshot UX audit:

- scope/family/typed-state contracts
- description-level HEALTH vs EVIDENCE grammar
- collapsed ID/Processed Records shells on non-Run boards
- docs, fixtures protocol, simulated usability remeasure

The **full audit** still requires **visual/layout/threshold enforcement**:

1. Visible scope badges (not only description text)
2. Color/threshold surgery (green 0/0, red expected zeros, SCRAPING health color, alert history colors)
3. First-viewport rebuild toward 1.0–1.5 viewports
4. Variable model: Run ID / Provider not silently global for NOW panels
5. Provider `SELECTION_REQUIRED`, DQ composite strip, Trust coverage-gated OK
6. Internal scroll purge + giant stat compression
7. Live screenshot regression + 152-panel matrix execution

This wave is **not** greenfield rewrite, not UID retirement, not re-open of DS2/DSA/DUX3 as failed.
This wave is **DUX4 = pixels enforce DUX3 contracts**.

## Accepted decisions (normative)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Portfolio | Keep **7 stable UIDs** |
| 2 | SOT | Surgical edits to `grafana/dashboards/*.json` |
| 3 | Titles | Visible scope markers allowed only with **updated title contracts/tests** (DUX4-01 first) |
| 4 | Metrics | No invent metrics; no Prom `run_id` labels |
| 5 | Incident | Read-only |
| 6 | Measurement | Usability **proxies only** (no MTT*) |
| 7 | Grammar | First-screen cell = `scope × family × state × evidence × action` (DUX3 contracts) |

## Constraints

- ADR-010 optional Grafana; no required Docker/Redis
- Tech-debt budgets must not increase
- Preserve panel IDs where possible; rollback unit = one PR/board
- Scenes/viz/UID cutover remain track-only unless gated

## Portfolio

| uid | Audit role |
| --- | --- |
| `bioetl-control-plane-v1` | Trust / Recovery |
| `bioetl-overview-v2` | Overview |
| `bioetl-runtime` | Pipeline Diagnostics |
| `bioetl-provider-health-v2` | Provider Health |
| `bioetl-dq-v2` | Data Quality |
| `bioetl-incident-v1` | Incident Workspace |
| `bioetl-run-explorer-v1` | Run Explorer |

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DUX4-00 | [#7088](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7088) | meta | epic | Dashboard visual enforcement residual (post-DUX3 / full UX audit) |
| DUX4-01 | [#7089](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7089) | P0 | V0 | Title-contract harness for optional `[SCOPE/FAMILY]` markers |
| DUX4-02 | [#7090](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7090) | P0 | V0 | Field-override inventory (zeros, SCRAPING, alert history, Trust) |
| DUX4-03 | [#7091](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7091) | P0 | V0 | Import 152-panel redesign matrix → tracked inventory |
| DUX4-10 | [#7092](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7092) | P0 | V1 | Visible scope strip/badges on all first-screen cells |
| DUX4-11 | [#7093](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7093) | P0 | V1 | Runtime — neutral SCRAPING color + NOW vs RUN grid separation |
| DUX4-12 | [#7094](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7094) | P0 | V1 | Provider — SELECTION_REQUIRED + kill green 0/0 + latency empty-state fix |
| DUX4-13 | [#7095](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7095) | P0 | V1 | DQ — composite Health×Evidence×Impact×Applicability strip |
| DUX4-14 | [#7096](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7096) | P0 | V1 | Trust — coverage-gated Safety/Integrity + red-zero purge |
| DUX4-15 | [#7097](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7097) | P0 | V1 | Incident — suspect WORKFLOW columns + real First Action CTAs |
| DUX4-16 | [#7098](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7098) | P1 | V1 | Overview — freshness + blast radius above fold |
| DUX4-17 | [#7099](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7099) | P0 | V1 | Alert history color series fix (firing ≠ green success) |
| DUX4-20 | [#7100](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7100) | P1 | V2 | Viewport budget pass (target lengths from audit §4) |
| DUX4-21 | [#7101](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7101) | P1 | V2 | Giant stats → max w=6 h=3–4; ≤4 verdict cells |
| DUX4-22 | [#7102](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7102) | P1 | V2 | Internal scrollbar purge on triage text panels |
| DUX4-23 | [#7103](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7103) | P1 | V2 | Enforce no first-screen accounting outside Run Explorer |
| DUX4-24 | [#7104](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7104) | P1 | V2 | Dominant viz per board (timeline/funnel/matrix) |
| DUX4-25 | [#7105](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7105) | P1 | V2 | Operator tables ≤4–7 key columns |
| DUX4-30 | [#7106](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7106) | P1 | V3 | Run ID select-in-explorer only; optional handoff context |
| DUX4-31 | [#7107](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7107) | P1 | V3 | Provider variable not global-required |
| DUX4-32 | [#7108](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7108) | P1 | V3 | Stage variable Diagnostics/DQ only; no literal `unknown` default |
| DUX4-33 | [#7109](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7109) | P1 | V3 | Selecting run_id derives/locks pipeline + run_type |
| DUX4-34 | [#7110](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7110) | P1 | V3 | Data-link contract under new variable rules |
| DUX4-40 | [#7111](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7111) | P2 | V4 | Token/color contract + icons + contrast measure |
| DUX4-41 | [#7112](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7112) | P2 | V4 | Live screenshot regression 1366/1440/1920 |
| DUX4-42 | [#7113](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7113) | P2 | V4 | Semantic fixtures wired to tests/render |
| DUX4-43 | [#7114](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7114) | P2 | V4 | Live usability proxy remeasure |
| DUX4-44 | [#7115](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7115) | P3 | track | Track Scenes tabs / viz / UID cutover |

## Delivery order

1. **PR-V0** DUX4-01 → DUX4-02 → DUX4-03 (harness before pixels)
2. **PR-V1** DUX4-10…17 (semantic safety; parallel by board after V0)
3. **PR-V2** DUX4-20…25 (layout density)
4. **PR-V3** DUX4-30…34 (variables/navigation)
5. **PR-V4** DUX4-40…43 (governance)
6. **Track** DUX4-44

## Wave exit criteria

### V0
- [ ] Title contracts accept or document scope markers without suite red
- [ ] Override inventory committed for zero/SCRAPING/alert/Trust color risks
- [ ] 152-panel matrix tracked with panel ids

### V1
- [ ] Visible scope on every first-screen cell
- [ ] No green 0/0; no red expected zero; SCRAPING not health-green
- [ ] Runtime NOW vs RUN not peer health
- [ ] Provider empty → SELECTION_REQUIRED
- [ ] DQ single composite strip; Trust coverage-gated OK
- [ ] Incident suspects show selected vs affected pipeline

### V2
- [ ] Viewport budgets met (proxy from layout y-span)
- [ ] ≤4 verdict cells; giant stats compressed
- [ ] No internal scroll on triage text
- [ ] One dominant viz per board

### V3
- [ ] Run ID / Provider / Stage variable rules as audit §6
- [ ] Data-links preserve time/vars; run_id only run-scoped

### V4
- [ ] Live screenshots + fixtures + proxy remeasure documented
- [ ] Track items remain non-blocking

## Rejected

- Greenfield rewrite / second dashboard monorepo
- Delete Trust or DQ UID
- Incident write-path
- Invent metrics / Prom `run_id`
- Causal MTT* claims

## Evidence anchors

- Full audit summary (session): BIOETL-GRAFANA-UX-AUDIT-20260729-085334
- DUX3 contracts: `docs/03-guides/dashboards/dux3-residual-contracts.md`
- DUX3 inventory: `docs/03-guides/dashboards/dux3-first-screen-inventory.json`
- Apply residual (desc-level): `scripts/ops/observability/grafana/apply_dux3_residual.py`
- Bodies: `.github/ISSUES/_dux4_bodies/`

## Publish record

- After `gh issue create`: fill Issue column + `reports/quality/dux4-2026-07-29-issue-publish.json`
