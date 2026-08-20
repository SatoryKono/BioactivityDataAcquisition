---
id: prompt.audit.cycle.dashboards
version: 1.1.0
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
  - INCLUDE_PIPELINE
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
  - grafana/dashboards
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/00-project/ai/prompts/library/observability/dashboard-panel-audit.md
  - docs/00-project/ai/prompts/library/observability/bi-dashboard-acceptance.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing panels not in shipped JSON
  - Inventing DASH-* IDs that already exist in DASHBOARD_REQUIREMENTS.md
  - Data FAIL from a screenshot alone
  - Treating visual-semantics PASS as no visual defects
  - Conflating FIRST_WINDOW_Y with FIRST_LOAD_Y_MAX
  - Aesthetic-only defects without task/readability/risk
  - Starting monitoring without operator approval
  - Running grafana-six/* or observability-seq as a second full pass
  - One GitHub issue per cosmetic nit when the root cause is shared
  - Empty form cycles
tags: [observability, dashboard, grafana, render, design, cycle, operator]
summary: Cyclic dashboard audit bound to DASHBOARD_REQUIREMENTS.md (DASH-*, bands, gates)
max_body_lines: 270
---

# Cyclic dashboard render + design audit

N-итерационный аудит **presentation-plane** семи shipped UID.
Контракт: `fragments/dashboard-requirements-audit.md` +
`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`.

Missing series / recording rules — сначала `prompt.audit.cycle.telemetry`.
Data FAIL только с query evidence. Не изобретать `DASH-*`.

| Card | Role |
| --- | --- |
| `prompt.observability.dashboard-panel-audit` | per-panel render status |
| `prompt.observability.bi-dashboard-acceptance` | BI-V/L/D checks |
| `prompt.observability.group-scalar-density-audit` | `density-scalar` method |

Skill: `observability-dashboard`. Loop: `prompt.audit.orchestrator`.
Default **`N=10`**, **`MODE=full`**, **`DEPTH=full`**, **`MONITORING=false`**,
`USER_ROLE=operator`. Пустые циклы запрещены.

**Routing:** inside `prompt.audit.sequential-run` run the full `CONTOURS`
below. Do **not** also run `prompt.observability.sequential-run` on the same
SHA. `grafana-six/*` → STOP.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `grafana/dashboards` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `DEPTH` | `full` (`quick` \| `detailed` \| `full`) |
| `AUDIT_MODE` | `full` \| `differential` |
| `CONTOURS` | `render,density-area,density-scalar,fill,fit,reflow,visual,layout,data,copy,safety` |
| `VIEWPORT` | `1366x768` |
| `THEME` | `dark` (also record `light`) |
| `ZOOM` | `100` (Tier-2: `200` browser zoom, not CSS `zoom`) |
| `USER_ROLE` | `operator` |
| `MONITORING` | `false` |
| `INCLUDE_PIPELINE` | `true` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/dashboard-audit-cycle-<shortsha>` |

## BioETL anchors

- Requirements: `docs/01-requirements/DASHBOARD_REQUIREMENTS.md`
- Budgets: `docs/03-guides/dashboards/contracts/layout-budgets.yaml`
- JSON: `grafana/dashboards/` · verdicts: `verdict-ontology.md`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty → worktree.
2. Confirm seven UIDs + answer-panel map (fragment). Empty SCOPE → STOP.
3. Run §8 static gates from the fragment. Record SHA.
4. `run_id = <UTC>-dash-cycle-<shortsha>`
5. Artifacts: `reports/audit-runs/<run_id>/` +
   `reports/audit/dashboard-cycle/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | `uid \| panel_id \| y \| band \| type \| datasource`. Baseline SHA. |
| **B Contours** | Only names in `CONTOURS`. Rules in the fragment. |
| **C Normalize** | `checks.json` + `findings.json` with `requirement_id`. `surface_score` 0–3. Dedupe `uid+panel_id+requirement_id`. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN. Title `[<uid>][<DASH-id>][P#] …`. Cap MAX_ISSUES. |
| **E Fix** | WORK_BRANCH; minimal JSON/query/script; no overflow-clip; no budget raises. |
| **F Validate** | Re-run §8 gates + affected panels. PR if ALLOW_PUSH. Delta. |

### Contours (see fragment for rules)

| Contour | Requirement slice |
| --- | --- |
| `render` | per-panel `OK` \| `Expected Empty` \| `Defect` \| `Not Verifiable` |
| `density-area` | `DASH-DENSITY-001` |
| `density-scalar` | `DASH-DENSITY-002` + `report-dashboard-scalar-density --check` |
| `fill` | zero vs empty vs UNKNOWN (`DASH-STATE-*`) |
| `fit` | `DASH-FIT-001`…`005` (in-panel scroll ≠ page scroll) |
| `reflow` | `DASH-REFLOW-001` Dark/Light × 100%/200% browser zoom |
| `visual` | BI-V-* + `DASH-COLOR-001` / typography floors |
| `layout` | BI-L-* + first-window answer (`DASH-FIRST-001`, `DASH-FIT-003`) |
| `data` | BI-D-*; FAIL only with query/HTTP/JSON |
| `copy` | `DASH-COPY-*`, `DASH-TIME-001` |
| `safety` | `DASH-SEC-001`, `DASH-DATA-003/004`, `DASH-STATE-005` |

`INCLUDE_PIPELINE=true`: render/preflight scripts, scenes/parity, CI dashboard
jobs. Tag `pipeline`. Live UI only if `MONITORING=true`.

## Focus checklist (each cycle)

- [ ] Seven UIDs + answer panels still in first window
- [ ] Every finding has `requirement_id` or `GAP`
- [ ] Bands recorded (`first_window` ≠ `first_load`)
- [ ] Both density metrics measured
- [ ] CURRENT / RANGE / exact-run not peer badges
- [ ] §8 gates re-run after fixes
- [ ] `MONITORING=false` live gaps are NV, not defects
- [ ] No grafana-six / second observability-seq pass

## Stop

Empty SCOPE. Invented panels or `DASH-*`. Data FAIL from screenshot.
Start monitoring without approval. Overflow-clip to “fix” `DASH-FIT-004`.
Orchestrator hard-stop.

## Success

- Per-panel render status + BI checks + `requirement_id` under the run dir
- §8 gates green or residual tracked
- `surface_score` 0–3; cap at 1 if any P0 remains
- `final-summary.md` after N or early-stop

## Related

- One-shot: `prompt.observability.dashboard-panel-audit`,
  `prompt.observability.bi-dashboard-acceptance`
- Density: `prompt.observability.group-scalar-density-audit`
- Data-plane: `prompt.audit.cycle.telemetry`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.telemetry` · Next: `prompt.audit.cycle.coderabbit`
