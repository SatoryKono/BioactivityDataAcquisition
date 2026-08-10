---
id: prompt.observability.dashboard-panel-audit
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - REPO
  - BASE
  - WORK_BRANCH
  - SCOPE
  - MODE
  - CYCLE_COUNT
  - PHASES
  - AUDIT_MODE
  - REQUIRE_GH_TRACKING
  - LANGUAGE
  - MONITORING
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - .codex/skills/observability-dashboard/SKILL.md
  - grafana/dashboards
anti_patterns:
  - CYCLE_COUNT=5 with mandatory empty cycles
  - Inventing panels not present in shipped JSON
  - Starting monitoring stack without operator approval
  - Full RULES/ADR dump in the paste
  - One GitHub issue per cosmetic nit when same root cause
tags: [observability, dashboard, grafana, audit, operator]
summary: Five-phase Grafana panel audit — render, GH issues, fix, closeout
max_body_lines: 160
---

# BioETL — Dashboard panel audit (5 phases, one session)

One session with **five named phases**. Do **not** treat `PHASES` as empty
re-cycles: `CYCLE_COUNT` stays `1`.

Skill: **observability-dashboard** (`.codex/skills/observability-dashboard/`).
Use real metric names from the repo. Do not invent panels missing from shipped JSON.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/dashboard-panel-audit` |
| `SCOPE` | `grafana/dashboards` (shipped JSON + panels) |
| `MODE` | `dashboard-audit` |
| `CYCLE_COUNT` | `1` |
| `PHASES` | `5` (named phases below — not empty re-cycles) |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `true` |
| `LANGUAGE` | `ru` |
| `MONITORING` | start `docker-compose.monitoring.yml` **only** if UI/render required and operator approved |

## Phase 1 — Inventory

- List shipped dashboards under `grafana/dashboards/` that exist in this checkout
- Table: `dashboard | uid/title | panel_count | datasources | notes`

## Phase 2 — Render and evaluate every panel

For **each** panel in SCOPE:

- dashboard, panel title/id, type, datasource
- exact query/target from JSON
- render/check result (script and/or Grafana UI if monitoring started)
- status: `OK` | `Expected Empty` | `Defect` | `Not Verifiable`
- if defect, class:
  - `Backend defect`
  - `Dashboard query defect`
  - `Grafana/UI rendering defect`
  - `Operational datasource availability`

No finding without proof. If monitoring unavailable → `Not Verifiable` + exact blocker.

Also note browser/UX defects when UI is available: `bad data`, `query error`,
`panel error`, unexpected empty, clipped text, broken grid/height, unnecessary
scroll inside panels.

## Phase 3 — GitHub tracking

- Search open issues **before** create (no duplicates)
- One issue per root cause / panel-cluster
- Body: dashboard, panel ids, status, evidence, acceptance criteria
- Table: `finding | issue# | state`

## Phase 4 — Remediation

- Fix available defects on `WORK_BRANCH` (never `main`)
- Re-render/re-check only affected panels
- Focused tests/checks; PR for dashboard JSON / docs / product deltas
- Do not close blocked items; do not grow debt budgets

## Phase 5 — Closeout

For each issue from Phase 3:

- Confirm against `origin/main` + branch evidence
- Verdict: `DONE` | `VERIFIED_ALREADY_RESOLVED` | `BLOCKED`
- Issue comment with acceptance + commands; close if done

**Done table**

| Issue | Verdict | SHA/PR | Checks |
| --- | --- | --- | --- |

## Stop rules

- After Phase 2, if `NO_ACTIONABLE_FINDINGS` → stop (do not invent work)
- Do **not** run empty “cycles 2–5 for form”
- Prefer `VERIFIED_ALREADY_RESOLVED` when main already fixed

## Final report (short)

| Phase | Outcome | Issues open/closed | PR/SHA |
| --- | --- | --- | --- |
