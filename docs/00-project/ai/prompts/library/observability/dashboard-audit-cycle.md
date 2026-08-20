---
id: prompt.observability.dashboard-audit-cycle
version: 2.1.0
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
  - THEME
  - ZOOM
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
  - fragments/dashboard-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - .codex/skills/observability-dashboard/SKILL.md
  - grafana/dashboards
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
  - docs/00-project/ai/prompts/library/observability/bi-dashboard-acceptance.md
  - docs/00-project/ai/prompts/library/observability/dashboard-panel-audit.md
anti_patterns:
  - Empty cycles for form
  - Inventing panels not in shipped JSON
  - Inventing DASH-* IDs already in DASHBOARD_REQUIREMENTS.md
  - Data FAIL from screenshot alone
  - Treating visual-semantics PASS as no visual defects
  - Conflating FIRST_WINDOW_Y with FIRST_LOAD_Y_MAX
  - Aesthetic-only defects without task/readability/risk
  - Starting monitoring without operator approval
  - Repeating render/visual/layout/data when hosted by observability-seq
  - Raising debt budgets
  - One GitHub issue per cosmetic nit when same root cause
  - Full WCAG matrix dump when DEPTH=quick
tags: [observability, dashboard, grafana, audit, cycle, density, render, operator]
summary: Cyclic dashboard audit bound to DASHBOARD_REQUIREMENTS.md — contours, gates, theme/zoom
max_body_lines: 230
---

# Cyclic dashboard audit (render · density · fill · acceptance)

N-итерационный аудит семи shipped UID. Контракт:
`fragments/dashboard-requirements-audit.md` +
`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`.

| Card | Role |
| --- | --- |
| `prompt.observability.dashboard-panel-audit` | per-panel render |
| `prompt.observability.bi-dashboard-acceptance` | BI-V/L/D |
| `prompt.observability.group-scalar-density-audit` | `density-scalar` |

Skill: **observability-dashboard**. ADR-010: monitoring optional.

Default **`N=20`**, **`MODE=full`**, **`DEPTH=full`**, **`MONITORING=false`**,
`USER_ROLE=operator`, все **`ALLOW_*=true`**. Пустые циклы запрещены.
Early-stop: 2 подряд итерации без новых PROVEN P0/P1 и без regression.

**Host routing:** when this card is step 7 of
`prompt.observability.sequential-run`, set
`CONTOURS=density-area,density-scalar,fill,pipeline,fit` (do not repeat
render/visual/layout/data). Standalone / `prompt.audit.cycle.dashboards`
uses the full default.

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
| `CONTOURS` | `render,density-area,density-scalar,fill,fit,reflow,visual,layout,data,copy,safety` |
| `VIEWPORT` | `1366x768` (record actual if different) |
| `THEME` | `dark` (also record `light`) |
| `ZOOM` | `100` (Tier-2: `200` **browser** zoom; CSS `zoom` is not evidence) |
| `USER_ROLE` | `operator` |
| `MONITORING` | `false` |
| `INCLUDE_PIPELINE` | `true` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `10` |
| `LANGUAGE` | `ru` |

## BioETL anchors

- Requirements + `layout-budgets.yaml` (fragment)
- JSON: `grafana/dashboards/` · skill tooling: link only
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty → worktree.
2. Seven UIDs + answer-panel map. Empty SCOPE → STOP.
3. Run fragment §8 static gates.
4. `run_id = <UTC>-dash-cycle-<shortsha>`
5. Artifacts: `reports/audit/dashboard-cycle/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **0 Scope** | `full` = SCOPE; `differential` = `origin/BASE_BRANCH` ∩ SCOPE. |
| **A Inventory** | `uid \| panel_id \| y \| band \| type \| datasource`. |
| **B Contours** | Names in `CONTOURS`; rules in the fragment. |
| **C Normalize** | `checks.json` + `findings.json` with `requirement_id`. Dedupe. |
| **D Issues** | Title `[<uid>][<DASH-id>][P#] …`. Cap MAX_ISSUES. |
| **E Fix** | WORK_BRANCH; no overflow-clip; no budget raises. |
| **F Validate** | Re-run §8 gates; PR if ALLOW_PUSH. |
| **G Close / Post** | Close if ALLOW_CLOSE + acceptance. Delta. |

### Contours

See fragment. `render` statuses: `OK` \| `Expected Empty` \| `Defect` \|
`Not Verifiable`. No UI → NV + blocker, not FAIL.

### Theme / zoom (`reflow` + `visual`)

Record `VIEWPORT` / `THEME` / `ZOOM` on every artifact.

| Tier | When | Theme | Zoom |
| --- | --- | --- | --- |
| **1** | every cycle | dark + light | `100` |
| **2** | `DEPTH=detailed\|full` or Tier-1 fold/nav defects | same | `200` browser |

`INCLUDE_PIPELINE=true`: render scripts, scenes/parity, CI. Tag `pipeline`.

## Focus checklist (each cycle)

- [ ] Answer panels still in first window
- [ ] `requirement_id` on every PROVEN finding
- [ ] Both density metrics + FIT/reflow recorded or NV
- [ ] CURRENT / RANGE / exact-run not peer badges
- [ ] §8 gates re-run after fixes
- [ ] Live gaps at `MONITORING=false` are NV

## Outputs

```text
reports/audit/dashboard-cycle/<run_id>/
  run.json
  cycle-<i>/inventory.md, panel-matrix.csv, density-notes.md,
    fill-matrix.csv, checks.json, findings.json, issues.jsonl,
    summary.md, delta.md
  final-summary.md
```

## Final summary (required)

| Cycle | surface_score | P0–P1 open | density/fit notes | Issues | PR/SHA | Gate |
| --- | --- | --- | --- | --- | --- | --- |

Gate: `PASS` \| `WARN` \| `BLOCK`.

## Stop

`NO_ACTIONABLE_FINDINGS` / N / early-stop. Invented `DASH-*`. Data FAIL from
screenshot. Monitoring start without approval. Orchestrator hard-stop.

## Success

- Contours completed with `requirement_id` evidence
- PROVEN issues handled under ALLOW_*
- No new P0/P1 regression in post-check
- `final-summary.md` after N or early-stop

## Related

- `prompt.observability.dashboard-panel-audit`
- `prompt.observability.bi-dashboard-acceptance`
- `prompt.audit.cycle.dashboards`
- `prompt.observability.dashboard-full-cycle` — N=10 audit→issues→close with dual STOP
- Closeout: `prompt.closeout.grok`
