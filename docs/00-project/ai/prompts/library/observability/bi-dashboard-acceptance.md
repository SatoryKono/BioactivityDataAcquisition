---
id: prompt.observability.bi-dashboard-acceptance
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params:
  - SCOPE
  - PLATFORM
  - DEPTH
  - VIEWPORT
  - USER_ROLE
  - MODE
  - LANGUAGE
  - MONITORING
  - REQUIRE_GH_TRACKING
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
  - fragments/dashboard-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - .codex/skills/observability-dashboard/SKILL.md
  - grafana/dashboards
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
anti_patterns:
  - Aesthetic-only defects without readability/task/standard/risk
  - Data FAIL from screenshot alone
  - Inventing panels not in shipped JSON
  - Requiring Tableau/Power BI/Looker/dbt/GX on BioETL default path
  - Starting monitoring without operator approval
  - Full WCAG matrix dump when DEPTH=quick
tags: [observability, dashboard, bi, accessibility, acceptance, operator]
summary: BI dashboard acceptance — visual, layout, data contours with measurable checks
max_body_lines: 160
---

# BI dashboard acceptance audit

Acceptance audit across **three independent contours**: visual/typography,
layout/composition, data correctness. Not “like/dislike” — every FAIL/WARN
needs measurable evidence (see bi-check-schema).

**Engineering panel render → fix → closeout** remains  
`prompt.observability.dashboard-panel-audit`. Full check matrices (archive):  
`archive/campaigns/bi-dashboard-audit-kit-2026-08-11.md`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `grafana/dashboards` (or dashboard uid/path list) |
| `PLATFORM` | `grafana` (BioETL default; others only if proven in repo) |
| `DEPTH` | `quick` \| `detailed` \| `full` (full = quick+detailed+auto where tools exist) |
| `VIEWPORT` | e.g. `1366x768` (record actual) |
| `USER_ROLE` | `operator` (also `analyst` \| `manager` \| `executive` if proven) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` — start stack **only** if UI needed and operator sets `true` |
| `REQUIRE_GH_TRACKING` | `false` |

## BioETL facts

- Prefer shipped Grafana JSON under `grafana/dashboards/`
- Skill: `observability-dashboard` (link only; do not invent metrics/panels)
- Do not require Playwright/dbt/GX/Soda unless present in checkout
- Windows: `.\.venv-win\Scripts\python.exe` for repo Python tools

## Method

1. **Inventory** SCOPE dashboards/panels/variables/datasources (from JSON/API).
2. Run contours at `DEPTH` (IDs: `BI-V-*`, `BI-L-*`, `BI-D-*`):

### Visual (palette, type, contrast)

- Key text contrast (WCAG AA 4.5:1 normal / 3:1 large or non-text UI 3:1)
- Color not sole status encoding; hierarchy title→KPI→chart→label
- Labels/filters readable at VIEWPORT; units/number formats unambiguous
- Zoom/resize only if browser available; else `na`

### Layout (composition)

- Page goal clear in 5–10s; canonical answer panel in first window (`y < 18`)
- No duplicate panels without new analytic function; filter overload vs role
- Overview → driver → detail path; key insight not only in hover/drill
- Scalar density (`DASH-DENSITY-002`): scalar panels (`stat`/`gauge`/`bargauge`)
  `ρ = values/area`; each group `ρ > ρ(first_screen)`. Large single-value stats
  are sparse FAILs (exclude `timeseries`/`table`)

### Data (correctness)

- Classes: **source** vs **semantic** vs **presentation** error
- Period + last-refresh visible; unit/currency/scale consistent
- KPI vs control query delta (same filters); NULL/NaN not shown as real 0
- Bind FAILs to `DASH-*` (`requirement_id`); CURRENT vs RANGE vs exact-run are not peers
- Rate denominators; timezone; freshness vs SLA if defined; RLS if applicable
- **Data fail requires SQL/API/JSON query evidence** — not screenshot alone

3. **Release gate:** any **high** priority FAIL on KPI correctness, period/filters,
   freshness, units, RLS, or key accessibility content → **block acceptance**.
4. Medium items → backlog only with explicit risk note.
5. Emit `surface_score` from check scores (audit-scale map).

## Output

- `reports/audit/bi-dashboard/report.md`
- `reports/audit/bi-dashboard/checks.json`
- `reports/audit/bi-dashboard/findings.json` (PROVEN only for issues)
- optional: screenshots under same tree (no secrets)

## Stop

Empty SCOPE → STOP. No UI and check needs DOM → `na` / Not Verifiable.
Secret in capture → redaction + P0 process stop. `NO_ACTIONABLE_FINDINGS` if
all applicable checks pass or na.
