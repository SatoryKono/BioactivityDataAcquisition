---
id: prompt.observability.dashboard-audit-cycle
version: 2.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- codex
- any
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
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
- fragments/orchestrator-guards.md
- fragments/dashboard-requirements-audit.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- .codex/skills/observability-dashboard/SKILL.md
- grafana/dashboards
- docs/01-requirements/DASHBOARD_REQUIREMENTS.md
- docs/03-guides/dashboards/design-system.md
- docs/03-guides/dashboards/verdict-ontology.md
- docs/03-guides/dashboards/contracts/layout-budgets.yaml
- docs/03-guides/dashboards/contracts/requirement-coverage.yaml
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
- Empty cycles for form
- Inventing panels not in shipped JSON
- Inventing DASH-* IDs already in DASHBOARD_REQUIREMENTS.md
- Treating the fragment roster as newer than the audited JSON
- Data FAIL from screenshot alone
- Treating visual-semantics PASS as no visual defects
- Conflating FIRST_WINDOW_Y with FIRST_LOAD_Y_MAX
- Aesthetic-only defects without task/readability/risk
- Starting monitoring without operator approval
- Repeating render/visual/layout/data when hosted by observability-seq
- Raising debt budgets or performance-budgets.yaml
- One GitHub issue per cosmetic nit when same root cause
- Full WCAG matrix dump when DEPTH=quick
- Using a stale design-system L0 question when it disagrees with DASHBOARD_REQUIREMENTS.md §7
tags:
- observability
- dashboard
- grafana
- audit
- cycle
- density
- render
- operator
summary: Cyclic dashboard audit with per-UID palette, copy, data, answer panels, and panel roster
max_body_lines: 230
---
# Cyclic dashboard audit (render · density · fill · acceptance)

Read `fragments/dashboard-requirements-audit.md` before any contour. It is the
per-UID contract: question, answer panel, basis tokens, palette, typography,
data plane, and the panel roster. Shipped `grafana/dashboards/*.json` at the
audited SHA wins if the roster drifted. A missing required answer id is
`DASH-FIT-003`.

Skill: **observability-dashboard**. ADR-010: monitoring optional. Do not start
`docker-compose.monitoring.yml` unless `MONITORING=true` in this paste.

Default **`N=20`**, **`MODE=full`**, **`DEPTH=full`**, **`MONITORING=false`**,
`USER_ROLE=operator`, all **`ALLOW_*=true`**. Empty cycles are forbidden.
Early-stop: 2 consecutive iterations without new PROVEN P0/P1 and without
regression.

**Host routing:** step 7 of `prompt.observability.sequential-run` uses
`CONTOURS=density-area,density-scalar,fill,pipeline,fit`. Standalone uses the
full contour list.

## Per-dashboard answers

Questions are byte-equal to `DASHBOARD_REQUIREMENTS.md` §7. Ids are §7.1.

| UID | Question | Answer id |
| --- | --- | --- |
| `bioetl-run-explorer-v1` | Which pipelines ran most recently, and where are their reports? | `3010` |
| `bioetl-control-plane-v1` | Can the selected run be exactly replayed from saved inputs? | `9422` |
| `bioetl-overview-v2` | What is the saved assessment of the selected Run ID? | `9603`, `9002` |
| `bioetl-runtime` | What currently blocks runtime delivery? | `9401` |
| `bioetl-provider-health-v2` | Which provider is degraded/failing, and why? | `9101` |
| `bioetl-dq-v2` | What is the DQ assessment of the selected Run ID? | `9406` |
| `bioetl-incident-v1` | What is the highest-confidence active suspect? | `2010` |

Every cycle checks, for each UID, the fragment sections **Shared palette**,
**Shared text**, **Shared data and layout**, and that UID's panel table:

- state is labelled `OK` / `WARN` / `CRIT` / `UNKNOWN` (trust gates also
  `INCOMPLETE`); null is gray, never green
- `CURRENT` / `SELECTED RUN` / `TIME RANGE` are not peer badges
- authored body `>=16px`, headings `>=18.6667px`, clock `YYYY-MM-DD HH:MM`
- content titles use `Monitor|Inspect|Track|Compare|Review|Investigate`
- datasources are Prometheus, Grafana, or `BioETL Ops HTTP` only
- `y<18` is the visual fold; `y<28` is only the first-load query window

## Params

| Param | Default |
| --- | --- |
| `N` | `20` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE_BRANCH` | `main` |
| `WORK_BRANCH` | `fix/dashboard-audit-cycle-<shortsha>` (never main) |
| `SCOPE` | `grafana/dashboards` |
| `MODE` | `full` |
| `DEPTH` | `full` |
| `AUDIT_MODE` | `full` |
| `CONTOURS` | `render,density-area,density-scalar,fill,fit,reflow,visual,layout,data,copy,safety` |
| `VIEWPORT` | `1366x768` (record the actual viewport when it differs) |
| `THEME` | `dark` (also record `light`) |
| `ZOOM` | `100` (Tier-2: `200` browser zoom; CSS `zoom` is not evidence) |
| `USER_ROLE` | `operator` |
| `MONITORING` | `false` |
| `INCLUDE_PIPELINE` | `true` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `10` |
| `LANGUAGE` | `ru` |

Operator paste values override this table.

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty tree → worktree.
2. Seven UIDs from the fragment. Empty SCOPE → STOP.
3. Re-walk JSON into `panel-matrix.csv` and diff it against the fragment roster.
4. Run fragment §8 static gates.
5. `run_id = <UTC>-dash-cycle-<shortsha>`.
6. Artifacts: `reports/audit/dashboard-cycle/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **0 Scope** | `full` = SCOPE; `differential` = `origin/BASE_BRANCH` ∩ SCOPE. |
| **A Inventory** | `uid \| panel_id \| y \| band \| type \| datasource` from JSON. |
| **B Contours** | Apply the fragment rules for each name in `CONTOURS`. |
| **C Normalize** | `checks.json` + `findings.json` with `requirement_id`. Dedupe. |
| **D Issues** | Title `[<uid>][<DASH-id>][P#] …`. Cap MAX_ISSUES. |
| **E Fix** | WORK_BRANCH. No overflow-clip. No budget raises. |
| **F Validate** | Re-run §8 gates. PR if ALLOW_PUSH. |
| **G Close / Post** | Close only if ALLOW_CLOSE and acceptance holds. Write delta. |

### Contours

`render`: `OK` | `Expected Empty` | `Defect` | `Not Verifiable`. No UI → NV +
blocker, not FAIL. Do not mark data FAIL from a screenshot alone.

`copy` / `visual`: palette, type floors, clock, HTML roles, verdict description
tokens. `layout` / `fit` / `reflow`: fold 18 vs first-load 28, no straddle,
Tier-1 dark+light at 100%, Tier-2 browser zoom 200% when `DEPTH=full`.

`density-area` and `density-scalar`: both metrics, or NV. `data` / `safety`:
allowlisted datasources, no `run_id` Prometheus labels, no executable HTML.

`INCLUDE_PIPELINE=true`: render scripts, scenes/parity, CI. Tag `pipeline`.

Record `VIEWPORT` / `THEME` / `ZOOM` on every artifact.

## Focus checklist

- [ ] Each §7 answer id is a root panel with `y < 18`
- [ ] Palette, clock, and copy floors checked or NV
- [ ] `requirement_id` on every PROVEN finding
- [ ] Both density metrics and FIT/reflow recorded or NV
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

Gate: `PASS` | `WARN` | `BLOCK`.

## Stop

`NO_ACTIONABLE_FINDINGS` / N / early-stop. Invented `DASH-*`. Data FAIL from a
screenshot. Monitoring start without approval. Orchestrator hard-stop.

## Success

- Every in-scope UID checked against the fragment and the live JSON
- PROVEN issues handled under ALLOW_*
- No new P0/P1 regression in the post-check
- `final-summary.md` after N or early-stop

## Related

- `prompt.observability.dashboard-panel-audit`
- `prompt.observability.bi-dashboard-acceptance`
- `prompt.audit.cycle.dashboards`
- `prompt.observability.dashboard-full-cycle`
- Closeout: `prompt.closeout.grok`
