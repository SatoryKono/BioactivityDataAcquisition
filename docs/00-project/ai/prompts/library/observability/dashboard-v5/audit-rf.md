---
id: prompt.observability.dashboard-v5.audit-rf
version: 1.1.0
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
  - Treating leftover NV as FAIL when live UI was not actually rendered
  - Starting docker-compose.monitoring.yml when MONITORING is flipped back to false
  - Refactoring $pipeline / PromQL as if this were R-A/R-E
  - Reopening #8944-#8948
  - One issue per cosmetic nit with a shared root cause
tags: [observability, dashboard, grafana, v5, audit, rf, visual, operator]
summary: V5 R-F visual cycle — dark+light, 200% zoom, leftover NV; not a selector refactor
max_body_lines: 180
---

# BioETL — V5 R-F visual / NV cycle

Это **новый audit cycle**, не доработка селекторов. Язык: `{{LANGUAGE}}`.
Метод: `prompt.observability.dashboard-audit-cycle` (`N={{N}}`).

## Params

| Param | Default |
| --- | --- |
| `TASK` | R-F: light + 200% + leftover NV on shipped seven boards |
| `MODE` | `full` |
| `SCOPE` | `grafana/dashboards` (UIDs `bioetl-*-v1` / `bioetl-*-v2` / `bioetl-runtime`) |
| `LANGUAGE` | `ru` |
| `MONITORING` | `true` |
| `THEME` | `dark` (also re-check `light`) |
| `ZOOM` | `200` (Tier-2); also run Tier-1 `100` |
| `VIEWPORT` | `1920x1080` first, then `1366x768` first-window |
| `N` | `5` |

Render:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.observability.dashboard-v5.audit-rf `
  --param MODE=full --param LANGUAGE=ru --param MONITORING=true `
  --param THEME=dark --param ZOOM=200 --param VIEWPORT=1920x1080 --param N=5
```

## Жёсткое

`MONITORING=true` на этой карточке **разрешает** поднять
`docker-compose.monitoring.yml` для live render. Если стек не поднялся —
`GAP` / `Not Verifiable`, не defect. Если оператор вернул
`MONITORING=false` — live UI снова NV, не FAIL.

213 cycle-1 NV не превращать в FAIL пачкой.

Не трогать `$pipeline` binding, PromQL ID registry, HTTP catalog,
request fixtures — это R-A/R-E/R-B/R-C. Не открывать `#8944`–`#8948`.

## Контуры

1. Inventory панелей из shipped JSON (не выдумывать id).
2. `dark` @ `1920x1080` / `200%`: contrast, wrap, no horizontal scroll.
3. Тот же first-screen на `light` и на `1366x768` / `100%`.
4. `200%`: first window всё ещё отвечает на operator question.
5. Leftover NV: `GAP` vs defect; one issue per root cause.

Артефакты: `reports/audit/observability-seq/<utc>-v5-rf-<shortsha>/`.

## Done when

- [ ] `findings.json` + `report.md` с FACT/INFERENCE/GAP
- [ ] Live FAIL только с render evidence; стек не поднялся → GAP
- [ ] Issues только если `ALLOW_ISSUE_WRITE` (карточка cycle) и нет дубля
