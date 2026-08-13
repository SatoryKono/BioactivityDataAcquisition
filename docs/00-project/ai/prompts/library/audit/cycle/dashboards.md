---
id: prompt.audit.cycle.dashboards
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
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/00-project/ai/prompts/library/observability/dashboard-panel-audit.md
  - docs/00-project/ai/prompts/library/observability/bi-dashboard-acceptance.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing panels not in shipped JSON
  - Data FAIL from a screenshot alone
  - Aesthetic-only defects without task/readability/risk
  - Starting monitoring without operator approval
  - One GitHub issue per cosmetic nit when the root cause is shared
  - Empty form cycles
tags: [observability, dashboard, grafana, render, design, cycle, operator]
summary: Cyclic render and design audit of dashboards and individual panels
max_body_lines: 270
---

# Cyclic dashboard render + design audit

N-итерационный аудит **рендера и дизайна дашбордов и отдельных панелей**.
Контуры: render → density → fill → visual → layout → data.

Это **presentation-plane**. Missing series / recording rules — сначала
`prompt.audit.cycle.telemetry`. Data FAIL только с query evidence.

| Card | Contour |
| --- | --- |
| `prompt.observability.dashboard-panel-audit` | per-panel query/render status |
| `prompt.observability.bi-dashboard-acceptance` | visual / layout / data (BI-*) |

Skill: `observability-dashboard`. Loop shell: `prompt.audit.orchestrator`.
Default **`N=10`**, **`MODE=full`**, **`DEPTH=full`**, **`MONITORING=false`**,
все **`ALLOW_*=true`**. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `grafana/dashboards` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `DEPTH` | `full` (`quick` \| `detailed` \| `full`) |
| `AUDIT_MODE` | `full` \| `differential` |
| `CONTOURS` | `render,density,fill,visual,layout,data` |
| `VIEWPORT` | `1366x768` |
| `USER_ROLE` | `analyst` |
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

- Shipped JSON: `grafana/dashboards/`
- Design: `docs/03-guides/dashboards/design-system.md`
- Verdicts: `docs/03-guides/dashboards/verdict-ontology.md`
- Do not invent panels or metrics missing from shipped JSON
- ADR-010: start `docker-compose.monitoring.yml` only if UI/render is required
  and the operator set `MONITORING=true`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Inventory SCOPE paths that **exist**; empty → STOP.
3. `run_id = <UTC>-dash-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` +
   `reports/audit/dashboard-cycle/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Table `dashboard \| uid \| panel_count \| datasources \| notes`. Baseline SHA. |
| **B Contours** | Run each contour in `CONTOURS` (below). Evidence-first. |
| **C Normalize** | `checks.json` (bi-check-schema) + `findings.json` (PROVEN only). `surface_score` 0–3. Dedupe by panel-cluster / root-cause. |
| **D Issues** | Create if ALLOW_ISSUE_WRITE + PROVEN. Title `[dashboard][P#] one checkable outcome`. Cap MAX_ISSUES. |
| **E Fix** | WORK_BRANCH; minimal dashboard JSON / query / script fixes; re-check **affected** panels only. |
| **F Validate** | Re-render/re-check the fixed set. PR if ALLOW_PUSH. Delta: resolved / unchanged / regressed / new. |

### Contours

1. **`render`** — per panel: `OK` \| `Expected Empty` \| `Defect` \| `Not Verifiable`.
   Defect class: `Backend` \| `Dashboard query` \| `Grafana/UI rendering` \|
   `Operational datasource`. No UI → `Not Verifiable` + blocker (not FAIL).
2. **`density`** — signal vs chrome at VIEWPORT for USER_ROLE. Above-the-fold
   KPI; no competing equal-weight panels; time-to-first-insight 5–10s.
3. **`fill`** — true empty vs Expected Empty; placeholders; NULL rendered as 0;
   sparse tall rows; missing empty-state copy.
4. **`visual`** — BI-V-*: contrast, color-not-sole-status, type hierarchy, units.
5. **`layout`** — BI-L-*: page goal, fold KPI, overview→driver→detail, no key
   insight only in hover.
6. **`data`** — BI-D-*: FAIL only with SQL/API/JSON evidence. Period, units,
   denominators, source vs semantic vs presentation error.

If `INCLUDE_PIPELINE=true`: inspect render/preflight scripts and scenes/parity
ledgers. Tag `pipeline`.

## Focus checklist (each cycle)

- [ ] No invented panels/metrics outside shipped JSON
- [ ] Every panel has render status + evidence path
- [ ] Density: fold KPI + hierarchy + no duplicate analytic function
- [ ] Fill: empty-state intentional; no placeholder titles; NULL≠0 silent
- [ ] Visual/layout/data checks recorded (or `na` with blocker)
- [ ] Issues clustered by root-cause
- [ ] Fixes re-verified on affected panels only
- [ ] Monitoring stack not started unless MONITORING=true

## Stop

Empty SCOPE. Invented panels. Data FAIL from screenshot alone.
Start monitoring without approval. Aesthetic-only nits without task risk.
Orchestrator hard-stop.

## Success

- Per-panel render status + BI checks under the run dir
- Affected panels re-verified after fix
- `surface_score` 0–3; cap at 1 if any P0 remains
- `final-summary.md` after N or early-stop

## Related

- One-shot: `prompt.observability.dashboard-panel-audit`,
  `prompt.observability.bi-dashboard-acceptance`
- Data-plane: `prompt.audit.cycle.telemetry`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.telemetry` · Next: `prompt.audit.cycle.coderabbit`
