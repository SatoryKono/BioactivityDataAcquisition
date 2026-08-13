---
id: prompt.observability.dashboard-audit-cycle
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - REPO
  - BASE_BRANCH
  - WORK_BRANCH
  - SCOPE
  - MODE
  - DEPTH
  - AUDIT_MODE
  - CONTOURS
  - VIEWPORT
  - USER_ROLE
  - MONITORING
  - INCLUDE_PIPELINE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - LANGUAGE
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/bi-check-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - .codex/skills/observability-dashboard/SKILL.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
  - docs/00-project/ai/prompts/library/observability/bi-dashboard-acceptance.md
  - docs/00-project/ai/prompts/library/observability/dashboard-panel-audit.md
anti_patterns:
  - Empty cycles for form
  - Inventing panels not in shipped JSON
  - Data FAIL from screenshot alone
  - Aesthetic-only defects without task/readability/risk
  - Starting monitoring without operator approval (unless MONITORING=true and UI required)
  - Raising debt budgets
  - One GitHub issue per cosmetic nit when same root cause
  - Full WCAG matrix dump when DEPTH=quick
tags: [observability, dashboard, grafana, audit, cycle, density, render, operator]
summary: Cyclic dashboard audit N loops — render, density, fill, visual/layout/data, fix, re-verify
max_body_lines: 200
---

# Cyclic dashboard audit (render · density · fill · acceptance)

N-итерационный аудит дашбордов BioETL (Grafana-first): inventory → **render** →
**information density** → **panel fill / empty-state** → visual/layout/data
acceptance → issues → fix → re-verify → delta.

Domain methods (do not duplicate full text):

| Card | Contour |
| --- | --- |
| `prompt.observability.dashboard-panel-audit` | per-panel query/render status |
| `prompt.observability.bi-dashboard-acceptance` | visual / layout / data (BI-*) |

Skill: **observability-dashboard** (`.codex/skills/observability-dashboard/`).  
ADR-010: monitoring stack **optional** — start only if UI/render required.

Default **`N=20`**, **`MODE=full`**, **`DEPTH=full`**,
**`INCLUDE_PIPELINE=true`**, все **`ALLOW_*=true`**.

Пустые циклы запрещены. Early-stop: 2 подряд итерации без новых actionable
PROVEN P0/P1 и без regression.

## Params

| Param | Default |
| --- | --- |
| `N` | `20` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE_BRANCH` | `main` |
| `WORK_BRANCH` | `fix/dashboard-audit-cycle-<shortsha>` (never main) |
| `SCOPE` | `grafana/dashboards` (or uid/path list) |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
| `DEPTH` | `full` (`quick` \| `detailed` \| `full`) |
| `AUDIT_MODE` | `full` \| `differential` |
| `CONTOURS` | `render,density,fill,visual,layout,data` |
| `VIEWPORT` | `1366x768` (record actual if different) |
| `USER_ROLE` | `analyst` (or `manager` / `executive` / list) |
| `MONITORING` | `true` until UI needed; set `true` only with operator approval |
| `INCLUDE_PIPELINE` | `true` (render scripts, scenes ledger, CI dashboard gates if any) |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `LANGUAGE` | `ru` |

## BioETL anchors

- Shipped JSON: `grafana/dashboards/`
- Design: `docs/03-guides/dashboards/design-system.md`
- Verdict ontology: `docs/03-guides/dashboards/verdict-ontology.md`
- Skill tooling: screenshot refresh, render preflight, panel-audit (link only)
- Do not invent metrics/panels missing from shipped JSON
- Windows: `.\.venv-win\Scripts\python.exe` for repo Python tools

## Preflight

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or read-only for audit-only substeps.
3. Inventory SCOPE paths that **exist**; empty → STOP.
4. `run_id = <UTC>-dash-cycle-<shortsha>`
5. Artifacts: `reports/audit/dashboard-cycle/<run_id>/` (also OK under
   `reports/audit-runs/<run_id>/` if unified with other cycles).

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **0 Scope** | `full` = existing SCOPE only; `differential` = `origin/BASE_BRANCH` ∩ SCOPE. |
| **A Inventory** | Table: `dashboard \| uid \| panel_count \| datasources \| notes`. Baseline SHA. |
| **B Contours** | Run each contour in `CONTOURS` (below). Evidence-first. |
| **C Normalize** | `checks.json` (bi-check-schema) + `findings.json` (finding-schema, PROVEN only). `surface_score` 0–3. Dedupe by panel-cluster / root cause. |
| **D Issues** | If ALLOW_ISSUE_WRITE + PROVEN: create ≤ MAX_ISSUES_PER_ITERATION. Title `[dashboard][P#] one checkable outcome`. Else `issues.jsonl`. |
| **E Fix** | Branch WORK_BRANCH; minimal dashboard JSON / query / script fixes; re-check **affected** panels only. |
| **F Validate** | Re-render/re-check fixed set; if ALLOW_PUSH → PR + required checks; merge if ALLOW_MERGE. |
| **G Close / Post** | Close if ALLOW_CLOSE + acceptance. Per finding: resolved \| unchanged \| regressed \| new → `cycle-i/delta.md`. |

## Contours (detail)

Run only those listed in `CONTOURS` (default = all).

### 1) `render` — panel rendering

For **each** panel in SCOPE (method from `dashboard-panel-audit`):

| Field | Values |
| --- | --- |
| status | `OK` \| `Expected Empty` \| `Defect` \| `Not Verifiable` |
| defect class | `Backend` \| `Dashboard query` \| `Grafana/UI rendering` \| `Operational datasource` |

Also note: query error banner, panel error, clipped text, broken grid/height,
inner scroll, missing legend, wrong viz type for data shape.

No UI/monitoring → `Not Verifiable` + exact blocker (not FAIL).

### 2) `density` — information density

Assess **signal vs chrome** at VIEWPORT for `USER_ROLE`:

- Above-the-fold: primary KPI + explaining view visible without scroll
- Whitespace vs cramped: neither sparse “poster” nor unreadable packing
- Competing equal-weight panels without hierarchy → FAIL density
- Repeated metrics / decorative panels without new analytic function
- Filter/variable bar overload vs role (analyst vs executive)
- Time-to-first-insight target: **5–10s** for page goal
- Chart ink: labels/units present; avoid chartjunk; series count readable

Tag findings `category=density`. Prefer measurable layout evidence
(screenshot crop + panel list + fold line), not taste alone.

### 3) `fill` — panel fill / empty / placeholder

- True empty vs Expected Empty (document expected)
- Sparse panels (single number with wasted tall row) vs overloaded
- Placeholder/lorem/“Panel Title” leftovers
- NULL rendered as 0 without annotation
- Loading forever / no-data without empty-state copy
- Table/heatmap cells mostly blank without intentional filter
- Min-height / row span inconsistent with content volume

Tag findings `category=fill`.

### 4) `visual` — BI-V-* (from bi-dashboard-acceptance)

Contrast (WCAG AA when measurable), color-not-sole-status, type hierarchy
title→KPI→chart→label, units/number formats.

### 5) `layout` — BI-L-*

Page goal, above-fold KPI, duplicates, filter overload, overview→driver→detail
path, key insight not only in hover.

### 6) `data` — BI-D-*

**Data FAIL only with SQL/API/JSON query evidence** (not screenshot alone).
Period + last-refresh; unit/scale consistency; denominators; source vs semantic
vs presentation error classes.

### Pipeline (`INCLUDE_PIPELINE=true`)

Inspect render/preflight scripts, scenes/parity ledgers if present, CI jobs
touching dashboards. Tag `category=pipeline`. Do not start monitoring stack
unless `MONITORING=true` and UI required.

## Focus checklist (each cycle)

- [ ] No invented panels/metrics outside shipped JSON
- [ ] Every panel has render status + evidence path
- [ ] Density: fold KPI + hierarchy + no duplicate analytic function
- [ ] Fill: empty-state intentional; no placeholder titles; NULL≠0 silent
- [ ] Visual/layout/data checks recorded (or `na` with blocker)
- [ ] Issues clustered by root cause (not one cosmetic per panel)
- [ ] Fixes re-verified on affected panels only
- [ ] Debt budgets unchanged

## Outputs

```text
reports/audit/dashboard-cycle/<run_id>/
  run.json
  cycle-<i>/
    inventory.md
    panel-matrix.csv       # render status per panel
    density-notes.md       # fold / hierarchy / density
    fill-matrix.csv        # fill / empty-state
    checks.json            # bi-check-schema
    findings.json
    issues.jsonl
    summary.md
    delta.md
  final-summary.md
```

## Final summary (required)

| Cycle | surface_score | P0–P1 open | density/fill notes | Issues | PR/SHA | Gate |
| --- | --- | --- | --- | --- | --- | --- |

Gate: `PASS` \| `WARN` \| `BLOCK`  
Release block if high FAIL on KPI / period / freshness / units / key a11y / systemic render defects.

## Stop

- `NO_ACTIONABLE_FINDINGS` or N exhausted or early-stop
- Secret/data-loss risk; orchestrator hard-stop
- MONITORING start refused without approval when UI mandatory → mark blockers Not Verifiable

## Success

- Contours completed with evidence
- PROVEN issues handled under ALLOW_*
- No new P0/P1 regression in post-check
- `final-summary.md` after N=20 or early-stop

## Related

- `prompt.observability.dashboard-panel-audit`
- `prompt.observability.bi-dashboard-acceptance`
- Archive kit: `archive/campaigns/bi-dashboard-audit-kit-2026-08-11.md` (opt-in)
- Closeout: `prompt.closeout.grok`
