---
id: prompt.observability.dashboard-first-window-noscroll
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params:
  - TASK
  - MODE
  - SCOPE
  - WORK_BRANCH
  - LANGUAGE
  - MONITORING
  - VIEWPORT
  - ALLOW_PUSH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - grafana/dashboards
  - tests/integration/test_dashboard_operator_readability.py
  - tests/integration/test_dashboard_first_window_containment.py
  - tests/integration/test_dashboard_geometry_and_purpose_contracts.py
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Treating page scroll as the defect when the contract is in-panel scroll
  - Using overflow:hidden/auto/scroll on first-window HTML to hide overflow
  - Raising first_screen_max_panels, FIRST_WINDOW_Y, or VIEWPORT_ROWS
  - Adding first_window_overflow allowlist entries
  - Growing a table past the fold or overlapping 214/215/9603
  - Replacing Overview CURRENT 214/215
  - Starting monitoring unless MONITORING=true
  - New active script that grows active_script_count
tags: [observability, dashboard, grafana, first-window, scroll, containment, implement, operator]
summary: Implement DASH-FIT-004 — no internal scroll on first-window text/stat/table panels across the seven UIDs
max_body_lines: 160
---

# BioETL — first-window no-scroll (DASH-FIT-004)

Убери **внутреннюю** прокрутку панелей first window на всех семи shipped UID.
Не runtime SSOT. Язык: `{{LANGUAGE}}`.

Это **не** page-level scroll дашборда. Дефект — `scrollHeight > clientHeight`
или `scrollWidth > clientWidth` внутри root non-row панели с
`gridPos.y < FIRST_WINDOW_Y` (`18`).

## Params

| Param | Default |
| --- | --- |
| `TASK` | first-window no-scroll на семи UID |
| `MODE` | `implement` |
| `SCOPE` | `grafana/dashboards` + `layout-budgets.yaml` + containment tests |
| `WORK_BRANCH` | `fix/dash-first-window-noscroll` (never main) |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `VIEWPORT` | `1366x768` |
| `ALLOW_PUSH` | `true` (only `fix/*`) |

Windows: `.\.venv-win\Scripts\python.exe`. Чужой dirty WIP — worktree.
Skill: **observability-dashboard**.

## Контракт

| ID | Правило |
| --- | --- |
| `DASH-FIT-001` | `max(y+h)` root non-row ≤ `VIEWPORT_ROWS` (`18`) |
| `DASH-FIT-002` | не straddling fold (`y < 18 < y+h`) |
| `DASH-FIT-003` | не заменять Overview CURRENT `214`/`215` |
| `DASH-FIT-004` | first-window `text`/`stat`/`table`: нет internal scroll; `overflow:hidden\|auto\|scroll` в HTML запрещён (кроме nav spacer `height:0`) |
| `DASH-FIT-005` | first-window table имеет `max_rows` в `layout-budgets.yaml` и bind в JSON |

Допуск только `panel_containment_tolerance_px: 2`. Allowlist
`first_window_overflow` должен остаться пустым.

## Метод

1. Инвентарь: все root non-row `y < 18` на семи JSON.
2. Статика: `test_first_window_panels_do_not_declare_internal_scroll`;
   row-cap vs `limit`/`topk`; wrapText; `h` vs число строк (`cellHeight=sm`).
3. Если `MONITORING=true` — Playwright/render containment
   (`scrollHeight`/`clientHeight`). Иначе чинить по JSON-оценке и тестам;
   live render не обязателен.
4. Чинить **содержанием**, не клиппингом:
   - укоротить banner copy / `white-space:normal` / `overflow-wrap:anywhere`;
   - снизить `max_rows`/`topk`/`limitField` так, чтобы шапка+строки влезали в `h`;
   - wrap только именованной text-колонки при достаточной ширине;
   - увеличить `h` только если `y+h ≤ 18` и нет overlap.
5. Не поднимать `first_screen_max_panels`. Не двигать `9603` ниже `214`/`215`.

## Checks (обязательны)

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q `
  tests/integration/test_dashboard_operator_readability.py `
  tests/integration/test_dashboard_first_window_containment.py `
  tests/integration/test_dashboard_geometry_and_purpose_contracts.py
```

После правок `grafana/dashboards/**` readability gate обязателен (CI + pre-push).

## Done

Каждая first-window `text`/`stat`/`table` либо влезает без scroll, либо
`BLOCKED` с точным panel id, `gridPos`, причиной (rows vs `h`, wrap, copy)
и почему JSON-оценка недостаточна без live render.
