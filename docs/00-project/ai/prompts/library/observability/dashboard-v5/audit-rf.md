---
id: prompt.observability.dashboard-v5.audit-rf
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params:
  - TASK
  - MODE
  - SCOPE
  - LANGUAGE
  - MONITORING
  - THEME
  - ZOOM
  - VIEWPORT
  - N
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
  - fragments/reports-output.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/design-system.md
  - grafana/dashboards
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/00-project/ai/prompts/library/observability/dashboard-audit-cycle.md
anti_patterns:
  - Treating leftover NV as FAIL when MONITORING=false
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Refactoring $pipeline / PromQL as if this were R-A/R-E
  - Reopening #8944-#8948
  - One issue per cosmetic nit with a shared root cause
tags: [observability, dashboard, grafana, v5, audit, rf, visual, operator]
summary: V5 R-F visual cycle — light theme, 200% zoom, leftover NV; not a selector refactor
max_body_lines: 180
---

# BioETL — V5 R-F visual / NV cycle

Это **новый audit cycle**, не доработка селекторов. Язык: `{{LANGUAGE}}`.
Метод: `prompt.observability.dashboard-audit-cycle` (`N={{N}}`).

## Params

| Param | Default |
| --- | --- |
| `TASK` | R-F: light + 200% + leftover NV on shipped seven boards |
| `MODE` | `audit` |
| `SCOPE` | `grafana/dashboards` UIDs `bioetl-*-v1` / `bioetl-*-v2` / `bioetl-runtime` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` until operator sets `true` |
| `THEME` | `light` (also re-check `dark`) |
| `ZOOM` | `200` (Tier-2); Tier-1 remains `100` |
| `VIEWPORT` | `1366x768` first, then `1920x1080` |
| `N` | `1` |

## Жёсткое

`MONITORING=false` → live UI = `Not Verifiable`, **не** defect.
Не стартовать `docker-compose.monitoring.yml` без явного
`MONITORING=true`. 213 cycle-1 NV не превращать в FAIL пачкой.

Не трогать `$pipeline` binding, PromQL ID registry, HTTP catalog,
request fixtures — это R-A/R-E/R-B/R-C.

## Контуры

1. Inventory панелей из shipped JSON (не выдумывать id).
2. Light theme first-screen: contrast, wrap, no horizontal scroll.
3. 200% zoom: first window still answers the operator question.
4. Leftover NV: classify `GAP` vs real defect; one issue per root cause.

Артефакты: `reports/audit/observability-seq/<utc>-v5-rf-<shortsha>/`.

## Done when

- [ ] `findings.json` + `report.md` с FACT/INFERENCE/GAP
- [ ] NV не засчитаны как FAIL при `MONITORING=false`
- [ ] Issues только если `ALLOW_ISSUE_WRITE` (карточка cycle) и нет дубля
