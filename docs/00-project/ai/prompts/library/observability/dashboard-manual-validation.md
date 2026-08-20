---
id: prompt.observability.dashboard-manual-validation
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - REPO
  - BASE
  - SCOPE
  - LANGUAGE
  - MODE
  - MONITORING
  - ALLOW_ISSUE_WRITE
  - UIDS
  - THEME
  - ZOOM
  - VIEWPORT
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/dashboard-requirements-audit.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - grafana/dashboards
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Inventing DASH-* IDs
  - Treating MONITORING=false live DOM/screenshot gaps as dashboard defects
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Using CSS zoom on :root as DASH-REFLOW-001 evidence
  - Data FAIL from a screenshot without query/HTTP JSON
  - Reopening GitHub #8986 or cloning grafana-six as a second full pass
  - overflow:hidden clip as a DASH-FIT-004 fix
tags: [observability, dashboard, grafana, audit, manual, validation, operator]
summary: Manual validation of DASH-* rules that static pytest cannot prove — reflow, computed type, live FIT, render states; theme and zoom Dark/Light 100%/200%
max_body_lines: 180
---

# BioETL — manual validation (untestable DASH-*)

Не runtime SSOT. Язык: `{{LANGUAGE}}`. Shipped JSON = structure SSOT.
Live SHA-bound screenshots remain GitHub `#8986` — this card does **not**
reopen that issue.

Reuse, do not clone: `grafana-audit.visual`, `grafana-audit.layout`,
`dashboard-first-window-noscroll`, `bi-dashboard-acceptance`,
`dashboard-audit-cycle` contours `fit,fill`.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `origin/main` |
| `SCOPE` | `grafana/dashboards` (seven ADR-053 UIDs) |
| `LANGUAGE` | `ru` |
| `MODE` | `audit` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `UIDS` | `all` |
| `THEME` | `dark,light` |
| `ZOOM` | `100,200` |
| `VIEWPORT` | `1366x768` |

Windows: `.\.venv-win\Scripts\python.exe`. Skill: **observability-dashboard**.

## TASK

MODE=`audit`. SCOPE=`grafana/dashboards/*.json` (seven ADR-053 UIDs only).
SSOT: `docs/01-requirements/DASHBOARD_REQUIREMENTS.md`.
Fragment: `fragments/dashboard-requirements-audit.md`.
Do not invent DASH-* IDs. Do not start `docker-compose.monitoring.yml`
unless `MONITORING=true`. Dedup live render work against GitHub `#8986`.

For each UID 0..6, for each requirement below, record
`PASS` / `FAIL` / `Not Verifiable`:

1. `DASH-REFLOW-001` — Dark and Light at **browser** 100% and 200% on
   1366×768. CSS zoom on `:root` is not evidence. FAIL if page-level
   horizontal overflow, clipped titles/filters/KPIs/table headers, or
   unusable controls.
2. `DASH-TYPOGRAPHY-001` — computed style: authored body >= 16px, authored
   headings >= 18.6667px, Grafana-managed titles >= 14px. JSON `font-size`
   alone is not enough for native chrome.
3. `DASH-FIT-004` — first-window `text`/`stat`/`table`: in-panel
   `scrollHeight>clientHeight` or `scrollWidth>clientWidth` is FAIL
   (browser-rounding tolerance only). No `overflow:hidden` clip as a fix.
4. `DASH-RENDER-001` — classify every first-window data panel as
   `healthy` | `valid_empty` | `telemetry_absent` | `explicit_error` |
   `incomplete` | `loading` | `blank`. Those seven must remain
   distinguishable. Screenshot without query/HTTP JSON is not data proof.
5. `DASH-FIRST-001` — from the first window only, an operator can name
   state, confidence, basis, and the next action without opening a
   collapsed row.
6. `DASH-STATE-002` — grayscale or color-blind pass: status still readable
   from text/mappings, not color alone.
7. `DASH-COLOR-001` — area fills only in first window and paired with
   textual mapping; additional groups text/line only; Dark+Light contrast
   of fill vs label.

If `MONITORING=false`: live DOM/screenshot rows are `Not Verifiable` +
blocker, **not** a dashboard defect.

## Output

`reports/audit/observability-seq/<utc>-dash-manual-<shortsha>/`
with `findings.json` (`requirement_id` required) and `report.md`.

## Success

- Seven UIDs scored for the seven DASH-* rows
- `MONITORING=false` live rows are `Not Verifiable`, not FAIL
- `#8986` not reopened; grafana-six not run
- No `.env` edits; no debt-budget raise; no commit to `main`
