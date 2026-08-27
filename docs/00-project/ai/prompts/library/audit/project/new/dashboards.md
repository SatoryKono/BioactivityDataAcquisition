---
id: prompt.audit.project.new.dashboards
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - DEPTH
  - AUDIT_MODE
  - CONTOURS
  - VIEWPORT
  - THEME
  - ZOOM
  - USER_ROLE
  - MONITORING
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
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
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/00-project/ai/prompts/library/observability/dashboard-panel-audit.md
  - docs/00-project/ai/prompts/library/observability/bi-dashboard-acceptance.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing DASH-* IDs or panels not in shipped JSON
  - Data FAIL from a screenshot alone
  - Conflating FIRST_WINDOW_Y with FIRST_LOAD_Y_MAX
  - Starting monitoring without operator approval
  - Running grafana-six/* or a second full pass on the same SHA
  - One GitHub issue per cosmetic nit when uid+requirement_id+root_cause is shared
  - Closing issues against unmerged PR heads as if they were origin/main
  - Empty form cycles
  - ALLOW_* true by library default
  - Raising forensic timeout or debt budgets
tags: [observability, dashboard, grafana, render, design, cycle, operator]
summary: Improved cyclic dashboard audit bound to DASHBOARD_REQUIREMENTS.md — THEME/ZOOM contours, fail-closed ALLOW, stop when no new issues and no open cycle issues
max_body_lines: 260
---

# Improved cyclic dashboard audit

Улучшает `prompt.observability.dashboard-full-cycle` +
`prompt.observability.dashboard-audit-cycle` + `prompt.audit.cycle.dashboards`.
Skill: **observability-dashboard**. Data-plane gaps first:
`prompt.audit.project.new.telemetry`.

Library defaults: **`ALLOW_*=false`**, **`MONITORING=false`**,
**`ALLOW_MERGE=false`**. Не второй full-pass на том же SHA.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `grafana/dashboards` |
| `MODE` | `full` |
| `DEPTH` | `full` |
| `LANGUAGE` | `ru` |
| `CONTOURS` | `density-area,density-scalar,fill,fit,reflow,copy,safety` |
| `VIEWPORT` | `1366x768` |
| `THEME` | `dark,light` |
| `ZOOM` | `100` (Tier-2 `200` = **browser** zoom) |
| `USER_ROLE` | `operator` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `10` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/dash-cycle-new-<shortsha>` |

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. Seven shipped UID + DASHBOARD_REQUIREMENTS.md. Empty SCOPE → STOP.
3. `run_id = <UTC>-dash-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Static gates (not a substitute for step 1):

```text
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m scripts.engineering.qa check-dashboard-visual-semantics
python -m scripts.engineering.qa check-dashboard-performance-budgets
python -m scripts.engineering.qa report-dashboard-scalar-density --check
```

`check-dashboard-visual-semantics` PASS ≠ нет visual-дефектов.

## Cycle i = 1..N (strict 1→2→3)

### 1. Audit

All seven UID. THEME dark+light; ZOOM 100 and (DEPTH=full) 200 browser zoom.
First window `y < FIRST_WINDOW_Y`; first-load `y < FIRST_LOAD_Y_MAX` only for
PromQL/HTTP budget. Data FAIL needs query evidence. `requirement_id` = `DASH-*`
or `GAP`. Screenshot ≠ data proof.

Methods inside step 1 (not separate full audits): panel-audit, BI-V/L/D,
density-scalar, manual-validation **only** if MONITORING=true.

### 2. Issues

PROVEN P0–P2 (P3 if blocks `USER_ROLE=operator`). One issue per
`uid + requirement_id + root_cause`. Title `[<uid>][<DASH-id>][P#]`.
Cap MAX_ISSUES. `ALLOW_ISSUE_WRITE=false` → payloads only.

### 3. Fix-to-close

Fix on WORK_BRANCH. Re-scan touched UID. Close if ALLOW_CLOSE **and**
acceptance on `origin/main` (or operator accepted PR-head). Else BLOCKED.

## STOP (required)

After step 2: **STOP immediately** if `new_issues_i == 0` **and**
`open_cycle_issues == 0`. Then write `final-summary.md`.
If N exhausted with open cycle issues → BLOCK, no empty cycles.

`grafana-six/*` → STOP. Do not start monitoring unless MONITORING=true.

## Success

- Steps 1→2→3 honored; STOP met or N exhausted with BLOCK
- No invented DASH-*; no commit to `main`; budgets not raised
