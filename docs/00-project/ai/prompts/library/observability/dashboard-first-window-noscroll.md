---
id: prompt.observability.dashboard-first-window-noscroll
version: 1.1.0
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
  - THEME
  - ZOOM
  - N
  - CONSECUTIVE_PASS
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
  - tests/integration/test_dashboard_first_window_noscroll.py
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
  - Stopping after one green run instead of N runs and CONSECUTIVE_PASS
tags: [observability, dashboard, grafana, first-window, scroll, containment, implement, operator]
summary: Ultimate DASH-FIT-004 — no internal scroll on every first-window panel; mandatory pytest on code/tests/docs; N>=10 runs per UID then fix; CONSECUTIVE_PASS>=5; theme and zoom recorded
max_body_lines: 220
---

# Ultimate first-window no-scroll (DASH-FIT-004)

Ультимативно убери **внутреннюю** прокрутку **всех** панелей first window
на семи shipped UID. Не runtime SSOT. Язык: `{{LANGUAGE}}`.

Это **не** page-level scroll дашборда. Дефект — `scrollHeight > clientHeight`
или `scrollWidth > clientWidth` внутри **любой** root non-row панели с
`gridPos.y < FIRST_WINDOW_Y` (`18`).

## Params

| Param | Default |
| --- | --- |
| `TASK` | ultimate first-window no-scroll на семи UID |
| `MODE` | `implement` |
| `SCOPE` | `grafana/dashboards` + containment tests + CI |
| `WORK_BRANCH` | `fix/dash-first-window-noscroll` (never main) |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `VIEWPORT` | `1366x768` |
| `THEME` | `dark,light` |
| `ZOOM` | `100` (Tier-2 `200` browser zoom) |
| `N` | `10` (минимум прогонов теста на каждый UID) |
| `CONSECUTIVE_PASS` | `5` (минимум зелёных подряд на каждый UID) |
| `ALLOW_PUSH` | `true` (only `fix/*`) |

Windows: `.\.venv-win\Scripts\python.exe`. Чужой dirty WIP — worktree.
Skill: **observability-dashboard**.

## Обязательный тест (любое изменение code / tests / docs)

Гейт: `tests/integration/test_dashboard_first_window_noscroll.py`

Должен оставаться в:

- `.github/workflows/dashboard-first-window-noscroll.yml` (не path-filtered)
- Tests → Dashboard semantic release policy
- pre-push `check-dashboard-first-window-noscroll` (`src/` `tests/` `docs/` `grafana/`)

Нельзя сужать glob так, чтобы docs-only PR обходил гейт.

## Контракт

| ID | Правило |
| --- | --- |
| `DASH-FIT-001` | `max(y+h)` root non-row ≤ `VIEWPORT_ROWS` (`18`) |
| `DASH-FIT-002` | не straddling fold |
| `DASH-FIT-003` | не заменять Overview CURRENT `214`/`215` |
| `DASH-FIT-004` | **каждая** first-window панель: нет internal scroll; `overflow:hidden\|auto\|scroll` запрещён (кроме nav spacer `height:0`) |
| `DASH-FIT-005` | first-window table имеет `max_rows` и bind |

Allowlist `first_window_overflow` пустой. Не клиппинг.

## Цикл на каждый UID

Для каждого из семи JSON:

1. Прогон:
   `pytest tests/integration/test_dashboard_first_window_noscroll.py -k <stem>`
2. Если FAIL — чинить **содержанием** (copy, wrap, `max_rows`/`limit`/`h` при
   `y+h ≤ 18`), не `overflow:hidden`. Сбросить consecutive.
3. Если PASS — consecutive += 1.
4. Повторять, пока `runs >= N` **и** `consecutive >= CONSECUTIVE_PASS`.

Минимум 10 прогонов на UID. Минимум 5 зелёных **подряд**. После каждого
FAIL — правка до следующего прогона. Не поднимать `first_screen_max_panels`.

Live `scrollHeight` только при `MONITORING=true`. Иначе JSON-гейт + §8.

## Checks

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q `
  tests/integration/test_dashboard_first_window_noscroll.py `
  tests/integration/test_dashboard_operator_readability.py `
  tests/integration/test_dashboard_first_window_containment.py
```

## Done

На каждом UID: ≥ `N` прогонов, из них ≥ `CONSECUTIVE_PASS` зелёных подряд.
Иначе `BLOCKED` с panel id, `gridPos`, причиной.
