#!/usr/bin/env python3
"""Generate DUX4 issue pack + body files (visual enforcement residual)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ISSUES = ROOT / ".github" / "ISSUES"
BODIES_DIR = ISSUES / "_dux4_bodies"
PACK = ISSUES / "DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md"

PACK_TEXT = r'''# Dashboard visual enforcement residual — DUX4

**Status:** published (local pack; GH numbers filled after publish)
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
| DUX4-00 | _TBD_ | meta | epic | Dashboard visual enforcement residual (post-DUX3 / full UX audit) |
| DUX4-01 | _TBD_ | P0 | V0 | Title-contract harness for optional `[SCOPE/FAMILY]` markers |
| DUX4-02 | _TBD_ | P0 | V0 | Field-override inventory (zeros, SCRAPING, alert history, Trust) |
| DUX4-03 | _TBD_ | P0 | V0 | Import 152-panel redesign matrix → tracked inventory |
| DUX4-10 | _TBD_ | P0 | V1 | Visible scope strip/badges on all first-screen cells |
| DUX4-11 | _TBD_ | P0 | V1 | Runtime — neutral SCRAPING color + NOW vs RUN grid separation |
| DUX4-12 | _TBD_ | P0 | V1 | Provider — SELECTION_REQUIRED + kill green 0/0 + latency empty-state fix |
| DUX4-13 | _TBD_ | P0 | V1 | DQ — composite Health×Evidence×Impact×Applicability strip |
| DUX4-14 | _TBD_ | P0 | V1 | Trust — coverage-gated Safety/Integrity + red-zero purge |
| DUX4-15 | _TBD_ | P0 | V1 | Incident — suspect WORKFLOW columns + real First Action CTAs |
| DUX4-16 | _TBD_ | P1 | V1 | Overview — freshness + blast radius above fold |
| DUX4-17 | _TBD_ | P0 | V1 | Alert history color series fix (firing ≠ green success) |
| DUX4-20 | _TBD_ | P1 | V2 | Viewport budget pass (target lengths from audit §4) |
| DUX4-21 | _TBD_ | P1 | V2 | Giant stats → max w=6 h=3–4; ≤4 verdict cells |
| DUX4-22 | _TBD_ | P1 | V2 | Internal scrollbar purge on triage text panels |
| DUX4-23 | _TBD_ | P1 | V2 | Enforce no first-screen accounting outside Run Explorer |
| DUX4-24 | _TBD_ | P1 | V2 | Dominant viz per board (timeline/funnel/matrix) |
| DUX4-25 | _TBD_ | P1 | V2 | Operator tables ≤4–7 key columns |
| DUX4-30 | _TBD_ | P1 | V3 | Run ID select-in-explorer only; optional handoff context |
| DUX4-31 | _TBD_ | P1 | V3 | Provider variable not global-required |
| DUX4-32 | _TBD_ | P1 | V3 | Stage variable Diagnostics/DQ only; no literal `unknown` default |
| DUX4-33 | _TBD_ | P1 | V3 | Selecting run_id derives/locks pipeline + run_type |
| DUX4-34 | _TBD_ | P1 | V3 | Data-link contract under new variable rules |
| DUX4-40 | _TBD_ | P2 | V4 | Token/color contract + icons + contrast measure |
| DUX4-41 | _TBD_ | P2 | V4 | Live screenshot regression 1366/1440/1920 |
| DUX4-42 | _TBD_ | P2 | V4 | Semantic fixtures wired to tests/render |
| DUX4-43 | _TBD_ | P2 | V4 | Live usability proxy remeasure |
| DUX4-44 | _TBD_ | P3 | track | Track Scenes tabs / viz / UID cutover |

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
'''

TITLES: dict[str, str] = {
    "DUX4-00": "chore(grafana): DUX4 epic — visual enforcement residual post-DUX3 UX audit",
    "DUX4-01": "test(grafana): DUX4-01 title-contract harness for optional scope markers",
    "DUX4-02": "docs(grafana): DUX4-02 field-override inventory for zero/SCRAPING/alert colors",
    "DUX4-03": "docs(grafana): DUX4-03 import 152-panel redesign matrix to tracked inventory",
    "DUX4-10": "fix(grafana): DUX4-10 visible scope strip/badges on first-screen cells",
    "DUX4-11": "fix(grafana): DUX4-11 Runtime neutral SCRAPING + NOW vs RUN separation",
    "DUX4-12": "fix(grafana): DUX4-12 Provider SELECTION_REQUIRED + green 0/0 purge",
    "DUX4-13": "fix(grafana): DUX4-13 DQ composite Health×Evidence×Impact strip",
    "DUX4-14": "fix(grafana): DUX4-14 Trust coverage-gated Safety + red-zero purge",
    "DUX4-15": "fix(grafana): DUX4-15 Incident WORKFLOW suspect columns + real CTAs",
    "DUX4-16": "fix(grafana): DUX4-16 Overview freshness + blast radius above fold",
    "DUX4-17": "fix(grafana): DUX4-17 alert history color series (firing ≠ green)",
    "DUX4-20": "refactor(grafana): DUX4-20 viewport budget pass from UX audit",
    "DUX4-21": "refactor(grafana): DUX4-21 giant stats compression ≤4 verdict cells",
    "DUX4-22": "refactor(grafana): DUX4-22 purge internal scrollbars on triage text",
    "DUX4-23": "refactor(grafana): DUX4-23 no first-screen accounting outside Run Explorer",
    "DUX4-24": "refactor(grafana): DUX4-24 dominant viz per board (timeline/funnel/matrix)",
    "DUX4-25": "refactor(grafana): DUX4-25 operator tables ≤4–7 key columns",
    "DUX4-30": "fix(grafana): DUX4-30 Run ID select-in-explorer only",
    "DUX4-31": "fix(grafana): DUX4-31 Provider variable not global-required",
    "DUX4-32": "fix(grafana): DUX4-32 Stage variable Diagnostics/DQ only",
    "DUX4-33": "fix(grafana): DUX4-33 run_id selection derives pipeline + run_type",
    "DUX4-34": "fix(grafana): DUX4-34 data-link contract under new variable rules",
    "DUX4-40": "chore(grafana): DUX4-40 token/color contract + contrast measure",
    "DUX4-41": "test(grafana): DUX4-41 live screenshot regression 1366/1440/1920",
    "DUX4-42": "test(grafana): DUX4-42 semantic fixtures wired to tests/render",
    "DUX4-43": "docs(grafana): DUX4-43 live usability proxy remeasure",
    "DUX4-44": "chore(grafana): DUX4-44 track Scenes/viz/UID cutover",
}

META: dict[str, tuple[str, str]] = {
    "DUX4-00": ("meta", "epic"),
    "DUX4-01": ("P0", "V0"),
    "DUX4-02": ("P0", "V0"),
    "DUX4-03": ("P0", "V0"),
    "DUX4-10": ("P0", "V1"),
    "DUX4-11": ("P0", "V1"),
    "DUX4-12": ("P0", "V1"),
    "DUX4-13": ("P0", "V1"),
    "DUX4-14": ("P0", "V1"),
    "DUX4-15": ("P0", "V1"),
    "DUX4-16": ("P1", "V1"),
    "DUX4-17": ("P0", "V1"),
    "DUX4-20": ("P1", "V2"),
    "DUX4-21": ("P1", "V2"),
    "DUX4-22": ("P1", "V2"),
    "DUX4-23": ("P1", "V2"),
    "DUX4-24": ("P1", "V2"),
    "DUX4-25": ("P1", "V2"),
    "DUX4-30": ("P1", "V3"),
    "DUX4-31": ("P1", "V3"),
    "DUX4-32": ("P1", "V3"),
    "DUX4-33": ("P1", "V3"),
    "DUX4-34": ("P1", "V3"),
    "DUX4-40": ("P2", "V4"),
    "DUX4-41": ("P2", "V4"),
    "DUX4-42": ("P2", "V4"),
    "DUX4-43": ("P2", "V4"),
    "DUX4-44": ("P3", "track"),
}

BODY_TEXTS: dict[str, str] = {
    "DUX4-00": """## Summary

Execute **DUX4 visual enforcement** of the 2026-07-29 full Grafana UX audit after closed **DUX3** (#7053): turn contracts into **visible scope, correct colors, first-viewport layout, and variable rules** on the 7 stable UIDs.

## Why now

DUX3 delivered description-level grammar and collapsed shells. The full audit still shows operator-visible contradictions (SCRAPING vs Gold accounting, green 0/0, red expected zeros, UNKNOWN bucket, giant stats, internal scroll, global run_id leakage into NOW interpretation).

## Waves

| Wave | Codes | Exit |
| --- | --- | --- |
| V0 | 01–03 | harness + override inventory + 152-panel matrix |
| V1 | 10–17 | semantic safety in pixels |
| V2 | 20–25 | layout density |
| V3 | 30–34 | variables / navigation |
| V4 | 40–43 | governance / live evidence |
| Track | 44 | Scenes/viz/UID only |

## Constraints

- 7 UIDs; surgical JSON; ADR-010; no invent metrics; no Prom `run_id`
- Incident read-only; debt budgets non-increasing
- Title markers only after DUX4-01 test harness

## Predecessors

- #7053 DUX3 (closed)
- #6982 DSA / #6901 DS2 / #6800 DUX

## Source

BIOETL-GRAFANA-UX-AUDIT-20260729-085334 + `docs/03-guides/dashboards/dux3-residual-contracts.md`
""",
    "DUX4-01": """## Parent

_TBD_ (DUX4-00)

## Problem

Visible `[SCOPE/FAMILY]` title markers break existing exact-title integration contracts. DUX3 kept markers in descriptions only — operators still cannot see scope without hover/read.

## Scope

- [ ] Inventory all exact title assertions in `tests/integration/test_grafana*.py` / runtime dashboard tests
- [ ] Choose one approach (document decision):
  - **A)** allow optional prefix pattern `^[SCOPE/FAMILY] ` in helpers
  - **B)** dedicated scope text panels beside Status (no title change)
- [ ] Implement helper + update failing contracts
- [ ] Document convention in `dux3-residual-contracts.md` / operator-ux-v2

## Acceptance

- [ ] Grafana integration tests green with chosen approach
- [ ] Path open for DUX4-10 visible markers

## Files

- `tests/integration/test_grafana_config.py`
- `tests/integration/test_pipeline_runtime_dashboard.py`
- related grafana contract specs
""",
    "DUX4-02": """## Parent

_TBD_ (DUX4-00)

## Problem

Audit color defects require knowing current field overrides/thresholds. Without inventory, threshold PRs are guesswork.

## Scope

- [ ] Scan 7 JSON boards for `fieldConfig.defaults.thresholds`, `mappings`, `color`, table `color-background`
- [ ] Flag: zero green success, red at 0, SCRAPING/health shared colors, alert history series colors
- [ ] Commit inventory under `docs/03-guides/dashboards/` (tracked) as `dux4-field-override-inventory.json` (+ short md summary)
- [ ] Map each risk to DUX4-11…17 consumer issues

## Acceptance

- [ ] Every first-screen stat/table has override row
- [ ] P0 color risks explicitly listed

## Files

- `grafana/dashboards/*.json`
- `docs/03-guides/dashboards/`
""",
    "DUX4-03": """## Parent

_TBD_ (DUX4-00)

## Problem

Full audit claims a 152-panel redesign matrix. Repo needs a tracked 1:1 map to panel ids for execution tracking.

## Scope

- [ ] Build/import panel matrix from audit + live JSON walk
- [ ] Columns: uid, panel id, title, type, gridPos, scope, family, defect tags, target action, DUX4 issue code
- [ ] Store `docs/03-guides/dashboards/dux4-panel-redesign-matrix.json` (+ optional csv)
- [ ] Diff vs DUX3 first-screen inventory

## Acceptance

- [ ] Matrix covers all non-row panels on 7 UIDs
- [ ] Each P0 defect row links a DUX4-1x code

## Files

- `docs/03-guides/dashboards/dux3-first-screen-inventory.json`
- `grafana/dashboards/*.json`
""",
    "DUX4-10": """## Parent

_TBD_ (DUX4-00)

## Problem

Operators compare NOW/RANGE/RUN/WORKFLOW/GLOBAL cards as peers. Descriptions are insufficient.

## Scope

- [ ] Apply visible scope markers via DUX4-01 approach on all first-screen cells
- [ ] Provenance/context strip shows scope legend
- [ ] Same-PR docs + tests

## Depends on

- DUX4-01

## Acceptance

- [ ] Scope readable without Inspect/edit
- [ ] No wrong-scope peer presentation on first screen

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-11": """## Parent

_TBD_ (DUX4-00)

## Problem

Runtime shows Status=OK + SCRAPING health-colored next to RUN Gold accounting — false “completed run still scraping”.

## Scope

- [ ] Neutral lifecycle color/mapping for SCRAPING / phase chips
- [ ] Grid separation: NOW execution vs EVIDENCE telemetry vs RUN accounting (collapsed shell stays)
- [ ] Explicit dual-line target:
  - `NOW · Execution: …`
  - `RUN · <id>: COMPLETED …` only on RUN-scoped surfaces
- [ ] Tests + panel docs

## Depends on

- DUX4-01, DUX4-02

## Acceptance

- [ ] SCRAPING not health-green
- [ ] 5s: blocker vs telemetry gap vs historical run answerable

## Files

- `grafana/dashboards/bioetl-runtime.json`
- `tests/integration/test_pipeline_runtime_dashboard.py`
""",
    "DUX4-12": """## Parent

_TBD_ (DUX4-00)

## Problem

Empty provider + 0/0 checks + 0.00% failure rate rendered green; latency panel empty-state text mismatches title (circuit-breaker copy).

## Scope

- [ ] Empty provider → `SELECTION_REQUIRED` / N/A (not green zeros)
- [ ] Rates show `n/N` or N/A when denominator 0
- [ ] Purge green-at-zero thresholds on Healthy Checks / Total / Failure Rate
- [ ] Fix Adapter Request Latency empty-state content defect
- [ ] Collapse selected-provider detail until selection

## Depends on

- DUX4-02

## Acceptance

- [ ] Screenshot path empty provider cannot show green success zeros
- [ ] Empty-state text matches panel metric family

## Files

- `grafana/dashboards/bioetl-provider-health-v2.json`
""",
    "DUX4-13": """## Parent

_TBD_ (DUX4-00)

## Problem

DQ first screen shows UNKNOWN + VALID_EMPTY + dual 100% scores as peer truths.

## Scope

- [ ] Single composite strip: Health × Evidence freshness × Delivery impact × Applicability
- [ ] Demote dual volume/worst 100% cards below fold or into compact secondary
- [ ] Promote selected-run Medallion/exclusion evidence when run context present
- [ ] Keep NOW/RANGE/RUN non-peer

## Depends on

- DUX4-01, DUX4-02

## Acceptance

- [ ] No peer “all healthy 100%” when Status UNKNOWN/INCOMPLETE
- [ ] Delivery impact visible ≤30s proxy

## Files

- `grafana/dashboards/bioetl-dq-v2.json`
""",
    "DUX4-14": """## Parent

_TBD_ (DUX4-00)

## Problem

Replay Safety / Integrity can show OK while overall INCOMPLETE and blind spots list uninstrumented checks; Processed Records zeros red.

## Scope

- [ ] Coverage-gated mappings: OK only WITHIN OBSERVED COVERAGE; else PARTIAL
- [ ] Blind spots force reduced confidence on Safety chips
- [ ] Red-zero purge on expected empty accounting
- [ ] Keep Primary recovery CTA contract

## Depends on

- DUX4-02

## Acceptance

- [ ] Unconditional Safety OK impossible when blind spots material
- [ ] Expected zeros neutral

## Files

- `grafana/dashboards/bioetl-control-plane-v1.json`
""",
    "DUX4-15": """## Parent

_TBD_ (DUX4-00)

## Problem

Suspect tables can show other pipelines under selected pipeline without visible WORKFLOW relationship; First Action not actionable.

## Scope

- [ ] Columns/badges: Scope=WORKFLOW/GLOBAL, Affected pipeline, Selected pipeline, Relationship
- [ ] Replace prose “next best” with ≤4 real CTAs (links with time/vars)
- [ ] Keep Incident read-only
- [ ] Fix alert history colors if co-located (coordinate DUX4-17)

## Depends on

- DUX4-01

## Acceptance

- [ ] chembl_activity under chembl_assay selection is explainable in-panel
- [ ] First Action is actionable

## Files

- `grafana/dashboards/bioetl-incident-v1.json`
""",
    "DUX4-16": """## Parent

_TBD_ (DUX4-00)

## Problem

Overview is best triage board but lacks freshness/blast radius above fold; duplicate domain status below.

## Scope

- [ ] Compact freshness/confidence + blast-radius proxy above fold
- [ ] Collapse/duplicate domain-status cleanup
- [ ] Keep Status + Inputs + First Action core

## Acceptance

- [ ] 30s triage includes freshness/confidence
- [ ] ≤4 first-screen verdict cells

## Files

- `grafana/dashboards/bioetl-overview-v2.json`
""",
    "DUX4-17": """## Parent

_TBD_ (DUX4-00)

## Problem

Alert history uses green series for firing/pending; severity color is inverted/misleading.

## Scope

- [ ] Map firing/pending/resolved to non-success colors + text
- [ ] No color-background on non-severity columns
- [ ] Align Overview alert rows if same defect (warning·WARNING orange/red mismatch)

## Depends on

- DUX4-02

## Acceptance

- [ ] Firing never reads as green success
- [ ] Identical severity labels share color semantics

## Files

- `grafana/dashboards/bioetl-incident-v1.json`
- `grafana/dashboards/bioetl-overview-v2.json` (if applicable)
""",
    "DUX4-20": """## Parent

_TBD_ (DUX4-00)

## Problem

Page lengths exceed audit targets (Trust >3 vp, others >2).

## Scope

- [ ] Measure y-span proxy per board; reduce toward audit targets
- [ ] Collapse non-essential rows; move forensics below fold
- [ ] Document before/after y-span in residual note

## Acceptance

- [ ] Overview ≤1.2 vp proxy; Trust ≤2; others ≤1.5 where feasible without deleting evidence

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-21": """## Parent

_TBD_ (DUX4-00)

## Problem

Giant stats (UNKNOWN/OK/100%/0) dominate hierarchy.

## Scope

- [ ] Cap first-screen stats at ~w≤6, h≤4
- [ ] ≤4 verdict cells above fold per board
- [ ] Same-PR tests if gridPos contracted

## Acceptance

- [ ] No full-width single-word status card as sole hierarchy owner

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-22": """## Parent

_TBD_ (DUX4-00)

## Problem

Internal scrollbars on triage text panels (Run Scope, Provenance, Next Best Actions, etc.).

## Scope

- [ ] Shorten content to single-line/context chips
- [ ] Move runbook prose to panel description / docs link
- [ ] Eliminate internal vertical scroll on triage surfaces

## Acceptance

- [ ] Checklist at 1366: no internal scroll on listed audit panels

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-23": """## Parent

_TBD_ (DUX4-00)

## Problem

Accounting still leaks into non-Run first screens via shells or expanded rows.

## Scope

- [ ] Assert collapsed shells remain collapsed by default on non-Run boards
- [ ] Remove any non-collapsed ID/Processed peers above fold
- [ ] Guard test optional

## Acceptance

- [ ] Only Run Explorer shows ID/Processed as first-class above-fold KPIs

## Files

- `grafana/dashboards/*.json` (except run-explorer hub behavior)
""",
    "DUX4-24": """## Parent

_TBD_ (DUX4-00)

## Problem

Missing single dominant visualization per board (audit §7).

## Scope

- [ ] Overview: domain state timeline
- [ ] Runtime: stage timeline/Gantt-capable timeseries
- [ ] Provider: failure/degraded trend
- [ ] DQ: Medallion funnel
- [ ] Incident: alerts+suspects+history
- [ ] Trust: recovery decision matrix
- [ ] Run Explorer: selected-run funnel + top reasons
- [ ] No invent metrics — reuse existing panels/queries

## Acceptance

- [ ] One named dominant viz above fold per board

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-25": """## Parent

_TBD_ (DUX4-00)

## Problem

Wide forensic tables force horizontal scan and wrong severity coloring of non-severity columns.

## Scope

- [ ] Operator tables ≤4–7 key columns
- [ ] Technical columns → row details / explorer
- [ ] Coordinate with DUX4-17 color rules

## Acceptance

- [ ] First-screen tables scannable at 1366 without horizontal scroll (except named explorer)

## Files

- `grafana/dashboards/*.json`
""",
    "DUX4-30": """## Parent

_TBD_ (DUX4-00)

## Problem

Global Run ID makes historical RUN evidence look like NOW state.

## Scope

- [ ] Primary run selection in Run Explorer
- [ ] Other boards: optional run context handoff only; NOW panels ignore run_id for Prom
- [ ] Document variable ownership
- [ ] Update selector contracts/tests

## Acceptance

- [ ] Selecting run_id cannot recolor NOW health without RUN badge surface

## Files

- `grafana/dashboards/*.json`
- `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
""",
    "DUX4-31": """## Parent

_TBD_ (DUX4-00)

## Problem

Empty global Provider selector drives false UNKNOWN/0 health on Provider board and confuses others.

## Scope

- [ ] Provider required only on Provider Health (or derived from pipeline)
- [ ] No Selected Provider Detail row when empty
- [ ] Coordinate with DUX4-12

## Acceptance

- [ ] Empty provider → SELECTION_REQUIRED, not fleet-false health

## Files

- `grafana/dashboards/bioetl-provider-health-v2.json`
- selector contracts
""",
    "DUX4-32": """## Parent

_TBD_ (DUX4-00)

## Problem

Stage selector shows literal `unknown` and leaks into non-Diagnostics boards.

## Scope

- [ ] Stage only on Runtime/DQ as needed
- [ ] Values: Current / All / real stages — not `unknown`
- [ ] Update defaults + docs

## Acceptance

- [ ] No operator-facing Stage=unknown default

## Files

- `grafana/dashboards/*.json`
- `docs/03-guides/dashboards/variable-reference.md`
""",
    "DUX4-33": """## Parent

_TBD_ (DUX4-00)

## Problem

Incompatible combinations: selectors describe one execution context, run metadata another.

## Scope

- [ ] On run_id select: derive/lock pipeline + run_type from run identity
- [ ] Surface derived locks in UI text
- [ ] Tests for incompatible combos

## Depends on

- DUX4-30

## Acceptance

- [ ] Documented incompatible pairs rejected or auto-corrected

## Files

- dashboards + selector contracts + tests
""",
    "DUX4-34": """## Parent

_TBD_ (DUX4-00)

## Problem

Variable model changes can break handoffs.

## Scope

- [ ] Re-audit links vs navigation contracts under DUX4-30…33
- [ ] Preserve time range; run_id only run-scoped destinations
- [ ] Integration tests green

## Depends on

- DUX4-30…33

## Acceptance

- [ ] All first-class handoffs preserve workflow/pipeline/run_type/time

## Files

- `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- `grafana/dashboards/*.json`
- `tests/integration/test_grafana_*.py`
""",
    "DUX4-40": """## Parent

_TBD_ (DUX4-00)

## Problem

Color-only severity and unmeasured contrast.

## Scope

- [ ] Token/color contract + required icons/text
- [ ] Measure contrast vs theme tokens; fix critical failures
- [ ] Align with DUX3-03 bans

## Acceptance

- [ ] Contract + checklist committed; critical contrast fixed or waived with rationale

## Files

- `docs/03-guides/dashboards/`
- dashboard overrides as needed
""",
    "DUX4-41": """## Parent

_TBD_ (DUX4-00)

## Problem

Protocol exists (DUX3-32) without live fixed-viewport captures.

## Scope

- [ ] Capture 7 UIDs at 1366/1440/1920 with audit selection
- [ ] Assert no internal scroll / clip / bad horizontal scroll
- [ ] Store under `reports/observability/grafana/` (or allowed path)

## Depends on

- V1–V2 layout preferably landed

## Acceptance

- [ ] Baseline capture set + pass/fail notes

## Files

- render skill/scripts + reports
""",
    "DUX4-42": """## Parent

_TBD_ (DUX4-00)

## Problem

Fixture matrix documented but not wired.

## Scope

- [ ] Wire SELECTION_REQUIRED / VALID_EMPTY / MISSING / STALE / etc. to tests or render fixtures where possible
- [ ] No invent metrics

## Acceptance

- [ ] At least smoke coverage notes + any automated asserts added

## Files

- `docs/03-guides/dashboards/dux3-semantic-fixtures.md`
- tests/
""",
    "DUX4-43": """## Parent

_TBD_ (DUX4-00)

## Problem

Usability remeasure after DUX3 was simulated on JSON only.

## Scope

- [ ] Live or screenshot-assisted proxy remeasure (TTFS, clicks, screens)
- [ ] Update `reports/observability/usability-baseline.md`
- [ ] No MTT* claims

## Acceptance

- [ ] Post-DUX4 section with method + aggregates

## Files

- `reports/observability/usability-baseline.md`
""",
    "DUX4-44": """## Parent

_TBD_ (DUX4-00)

## Problem

Long-range items must not block visual enforcement.

## Scope (tracking only)

- [ ] Scenes Trust+DQ tabs (ADR-053)
- [ ] Contract-gated viz upgrades
- [ ] UID retirement criteria
- [ ] Incident write-path ADR+backend

## Acceptance

- [ ] Remains tracking-only until gates open

## Files

- ADR-053 + dashboard docs
""",
}


def main() -> None:
    BODIES_DIR.mkdir(parents=True, exist_ok=True)
    PACK.write_text(PACK_TEXT, encoding="utf-8", newline="\n")
    for code, body in BODY_TEXTS.items():
        (BODIES_DIR / f"{code}.md").write_text(
            body.strip() + "\n", encoding="utf-8", newline="\n"
        )
    title_lines = [f"- `{k}`: `{v}`" for k, v in TITLES.items()]
    titles_md = "# DUX4 suggested GitHub titles\n\n" + "\n".join(title_lines) + "\n"
    (BODIES_DIR / "TITLES.md").write_text(titles_md, encoding="utf-8", newline="\n")
    print(f"pack: {PACK}")
    print(f"bodies: {len(list(BODIES_DIR.glob('DUX4-*.md')))}")
    print(f"titles: {BODIES_DIR / 'TITLES.md'}")


if __name__ == "__main__":
    main()
