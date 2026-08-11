---
id: prompt.observability.dashboard-audit-cycle
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
  - DEPTH
  - AUDIT_MODE
  - CONTOURS
  - REQUIRE_GH_TRACKING
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_CYCLE
  - MONITORING
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
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Empty cycles for form (CYCLE_COUNT without new evidence)
  - Inventing panels not in shipped JSON
  - Data FAIL from screenshot alone
  - Starting monitoring without operator approval
  - Merge/close while ALLOW_* false
  - Raising debt budgets
  - One GitHub issue per cosmetic nit when same root cause
tags: [observability, dashboard, grafana, audit, cycle, operator]
summary: Cyclic Grafana/BI dashboard audit — inventory, acceptance, panels, fix, re-verify
max_body_lines: 180
---

# Cyclic dashboard audit

Итеративный цикл аудита дашбордов BioETL (Grafana-first): inventory →
acceptance + panel evaluation → issues → fix → re-verify → delta.

Default **`CYCLE_COUNT=1`**. Увеличивай N только по явной просьбе оператора.
Пустые «циклы для формы» запрещены.

Связанные cards (не дублируй полный текст):

| Card | Когда |
| --- | --- |
| `prompt.observability.bi-dashboard-acceptance` | контуры visual/layout/data |
| `prompt.observability.dashboard-panel-audit` | per-panel render/query → fix |
| `prompt.audit.orchestrator` | общий multi-domain loop (не dashboard-specific) |
| `prompt.closeout.grok` | закрытие issues после merge evidence |

Skill: **observability-dashboard** (`.codex/skills/observability-dashboard/`).

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/dashboard-audit-cycle` (never `main`) |
| `SCOPE` | `grafana/dashboards` (или uid/path list) |
| `MODE` | `audit` \| `audit+issues` \| `audit+fix` \| `full` |
| `CYCLE_COUNT` | `1` |
| `DEPTH` | `quick` \| `detailed` \| `full` (acceptance depth) |
| `AUDIT_MODE` | `full` \| `differential` (vs `origin/BASE` ∩ SCOPE) |
| `CONTOURS` | `panels,visual,layout,data` (subset allowed) |
| `REQUIRE_GH_TRACKING` | `true` if issues; else `false` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_CYCLE` | `5` |
| `MONITORING` | start stack **only** if UI needed + operator approved |
| `LANGUAGE` | `ru` |

`MODE=full` всё равно уважает `ALLOW_*` (fail-closed).

## Preflight (каждый run)

1. `git status --porcelain`; SHA; remote; base branch.
2. Dirty tree с чужими изменениями → worktree/clone или **read-only**.
3. Inventory: shipped JSON under SCOPE; skill/scripts for render if any.
4. `run_id = <UTC>-<shortsha>-dash`
5. Artifacts: `reports/audit/dashboard-cycle/<run_id>/`

## Cycle i = 1..CYCLE_COUNT

### Stage 0 — Scope lock

- `full`: only paths that **exist** under SCOPE
- `differential`: delta vs `origin/BASE` ∩ SCOPE
- Empty/invalid SCOPE → **STOP**

### Stage 1 — Inventory

Table: `dashboard | uid | panel_count | datasources | notes`  
Baseline commit SHA. Previous cycle findings path if i>1.

### Stage 2 — Contours (parallelizable, evidence-first)

Run only contours listed in `CONTOURS`:

| Contour | Focus | Output |
| --- | --- | --- |
| **panels** | per-panel query/render; OK / Expected Empty / Defect / Not Verifiable; defect class | panel matrix |
| **visual** | contrast, color-not-only, type hierarchy, units (BI-V-*) | checks |
| **layout** | goal, above-fold KPI, duplicates, filter overload (BI-L-*) | checks |
| **data** | period/freshness, reconcile delta, NULL-as-0, denominators (BI-D-*) | checks |

Rules:

- FACT / INFERENCE / ASSUMPTION; no aesthetic-only defects
- **Data FAIL** only with SQL/API/JSON query evidence (not screenshot alone)
- No UI → DOM/zoom/contrast → `na` / Not Verifiable, not fail
- Do not invent panels/metrics missing from shipped JSON

### Stage 3 — Normalize findings

- `checks.json` (bi-check-schema) + `findings.json` (finding-schema, PROVEN only)
- Map high/medium/low → P0–P3; `surface_score` 0–3
- **Release gate:** high FAIL on KPI/period/freshness/units/RLS/key a11y → block acceptance flag in summary
- Dedupe by root cause / panel-cluster / fingerprint

### Stage 4 — GitHub issues

If `REQUIRE_GH_TRACKING` and (`MODE` includes issues or `ALLOW_ISSUE_WRITE`):

- Search open issues first (dedupe)
- Create only **PROVEN** items; max `MAX_ISSUES_PER_CYCLE`
- If `ALLOW_ISSUE_WRITE=false`: write payloads to `issues.jsonl` only
- Title: `[dashboard][P#] one checkable outcome`

### Stage 5 — Remediation (optional)

Only if `MODE` is `audit+fix` or `full` and operator intent clear:

- Branch `fix/<slug>`; minimal diff; no drive-by
- Re-check **only** affected panels/checks
- Push/PR only if `ALLOW_PUSH`; merge only if `ALLOW_MERGE`
- Post-change: focused tests; debt budgets must not grow

### Stage 6 — Re-verify + cycle closeout

For each finding/issue this cycle:

| Field | Values |
| --- | --- |
| state | `FIXED` \| `OPEN` \| `BLOCKED` \| `VERIFIED_ALREADY_RESOLVED` \| `NOT_PROVEN` \| `WONT_FIX_OUT_OF_SCOPE` \| `regressed` \| `new` |

Delta vs previous cycle: resolved / remaining / new / regressed.

**Stop after cycle if:**

- `NO_ACTIONABLE_FINDINGS`
- `CYCLE_COUNT` exhausted
- Secret/data-loss risk without approval
- Budget / max issues / dirty-tree / missing perms (orchestrator-guards)

Early-stop (only if operator enabled): two consecutive cycles with no new
actionable P0/P1 and no regression.

## Outputs per cycle

```text
reports/audit/dashboard-cycle/<run_id>/
  run.json
  cycle-<i>/
    inventory.md
    checks.json
    findings.json
    panel-matrix.csv          # if panels contour
    issues.jsonl              # payloads and/or created numbers
    summary.md
  final-summary.md            # after last cycle
```

## Final summary (required)

| Cycle | surface_score | P0–P1 open | Issues | PR/SHA | Gate |
| --- | --- | --- | --- | --- | --- |

Gate: `PASS` \| `WARN` \| `BLOCK` (release gate).

Language: `LANGUAGE=ru` for narrative; paths/ids/commands original.

## Windows / runtime

- Python: `.\.venv-win\Scripts\python.exe` only from Win
- Prefer MCP slim; if down → repo search / `gh` / local scripts, mark `DEGRADED_MCP`
- Do not restate full RULES/ADR; link only
