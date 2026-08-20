---
id: prompt.observability.dashboard-full-cycle
version: 1.0.0
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
  - LANGUAGE
  - MONITORING
  - THEME
  - ZOOM
  - VIEWPORT
  - USER_ROLE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
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
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - grafana/dashboards
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Empty form cycles
  - Inventing DASH-* IDs or panels not in shipped JSON
  - Data FAIL from a screenshot alone
  - One GitHub issue per cosmetic nit when uid+requirement_id+root_cause is shared
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Running grafana-six/* or prompt.observability.sequential-run as a second full pass
  - Running prompt.audit.cycle.dashboards as a second full pass on the same SHA
  - Closing issues against unmerged PR heads as if they were origin/main
  - Raising debt budgets
  - Committing to main
  - Treating MONITORING=false live gaps as dashboard defects
tags: [observability, dashboard, grafana, audit, cycle, issues, closeout, operator]
summary: Unified N=10 dashboard cycle — full audit (render, design, fill, panels, theme, zoom) then GH issues then fix-to-close; stop when no new issues and no open cycle issues
max_body_lines: 280
---

# Unified dashboard full-cycle (audit → issues → close)

Один оркестратор на **семь shipped UID**. Не runtime SSOT.
Контракт: `fragments/dashboard-requirements-audit.md` +
`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`.
Skill: **observability-dashboard**.

Это **не** второй проход `prompt.observability.sequential-run` и **не**
`prompt.audit.cycle.dashboards` на том же SHA. Method-cards ниже —
контуры внутри шага 1, не отдельные полные аудиты.

| Method card | Контур внутри шага 1 |
| --- | --- |
| `grafana-audit.master` + `.visual` + `.layout` + `.data-integrity` | evidence, palette, IA, queries |
| `bi-dashboard-acceptance` | BI-V / BI-L / BI-D |
| `dashboard-panel-audit` phase 2 | каждая панель: render/fill/query |
| `dashboard-audit-cycle` contours | density-area, density-scalar, fill, fit, reflow, copy, safety |
| `dashboard-manual-validation` | live reflow/FIT/typography **только** при `MONITORING=true` |
| `dashboard-data-duplication` | внутри-UID дубли данных |
| `dashboard-panel-audit` phases 3–5 | шаблон issue / fix / close |

`grafana-six/*` → STOP. Не reopen `#8944`–`#8948`. Live SHA-render host
остаётся `#8986` (не плодить второй render-epic).

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE_BRANCH` | `main` |
| `WORK_BRANCH` | `fix/dash-full-cycle-<shortsha>` (never `main`) |
| `SCOPE` | `grafana/dashboards` (семь UID ADR-053) |
| `MODE` | `full` |
| `DEPTH` | `full` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `THEME` | `dark,light` |
| `ZOOM` | `100` (Tier-2 `200` **browser** zoom; CSS `zoom` не evidence) |
| `VIEWPORT` | `1366x768` |
| `USER_ROLE` | `operator` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `10` |

Windows: только `.\.venv-win\Scripts\python.exe`.

## Preflight

1. `git status --porcelain`; SHA; branch. Чужой dirty WIP → worktree.
2. Семь UID + answer-panel map (fragment / REQUIREMENTS §7.1). Пустой SCOPE → STOP.
3. `run_id = <UTC>-dash-full-<shortsha>`. Маркер issues: `Cycle-run: <run_id>`.
4. Ledger: `reports/audit/dashboard-full-cycle/<run_id>/`.
5. Статические гейты §8 (не вместо шага 1):

```text
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m scripts.engineering.qa check-dashboard-visual-semantics
python -m scripts.engineering.qa check-dashboard-performance-budgets
python -m scripts.engineering.qa report-dashboard-scalar-density --check
python -m scripts.engineering.qa report-dashboard-query-duplicates --check
python -m scripts.engineering.qa report-dashboard-promql-scope --check
```

`check-dashboard-visual-semantics` PASS ≠ нет visual-дефектов.

## Цикл i = 1..N

Выполнять **строго** 1 → 2 → 3. Не начинать шаг 2 без `findings.json` шага 1.
Не начинать шаг 3, пока шаг 2 не записал `issues.jsonl` (включая `created=0`).

### 1. Полный аудит

Все семь UID. Каждая data-bearing панель + text/nav first-window.

| Band | Правило |
| --- | --- |
| First window | root non-row, `y < FIRST_WINDOW_Y` (`18`) |
| First-load | `y < FIRST_LOAD_Y_MAX` (`28`) — только PromQL/HTTP budget |
| Additional group | Grafana `row` + children |

Снять (или `Not Verifiable` + blocker, если `MONITORING=false`):

- **Render / fill:** query из JSON; `OK` \| `Expected Empty` \| `Defect` \| `NV`;
  class Backend / Query / Grafana-UI / Datasource. HTTP `parser`/`root_selector`.
- **Design / visual:** palette `OK/WARN/CRIT/UNKNOWN`, area-fill только first
  window (`DASH-COLOR-001`), contrast Dark+Light, typography floors.
- **Layout / FIT:** overlap, fold, `DASH-FIT-001..005`, in-panel scroll,
  nav bus `0..6`, progressive disclosure.
- **Density:** `DASH-DENSITY-001` area; `DASH-DENSITY-002` scalar.
- **Data:** shipped metrics only; no `run_id` Prom labels; CURRENT vs RANGE vs
  exact-run HTTP; zero vs empty vs UNKNOWN (`DASH-STATE-001/003/004/ZERO-001`).
- **Copy / safety:** action verbs, empty-state vs backend-unavailable,
  `DASH-SEC-001`, `DASH-TIME-001`, `DASH-COPY-008`.
- **Reflow:** Dark+Light, 100% и (DEPTH=full) 200% **browser** zoom, 1366×768.
- **Duplication:** intra-UID; не сносить `DASH-FIT-003` / `DASH-FIT-005`.

Каждый PROVEN finding: `requirement_id` (`DASH-*` или `GAP`).
Скриншот не доказывает данные. FACT / INFERENCE / GAP / CONTRADICTION.

Выход шага 1: `cycle-<i>/inventory.md`, `panel-matrix.csv`, `findings.json`.

### 2. GitHub issues

Только PROVEN P0–P2 (P3 — если блокирует `USER_ROLE=operator`).

1. Search open **and closed** issues + open PRs (14 дней) + ledger этого `run_id`.
2. Один issue на `uid + requirement_id + root_cause` (не на каждую панель-косметику).
3. Title: `[<uid>][<DASH-id>][P#] one checkable outcome`
4. Body MUST include: `Cycle-run: <run_id>`, panel ids, evidence, acceptance,
   `requirement_id`.
5. Cap `MAX_ISSUES_PER_ITERATION`. Остаток — в `deferred.jsonl`.
6. Не recreate closed issue, если есть open fix PR.

`ALLOW_ISSUE_WRITE=false` → только payloads, не `gh issue create`.

Выход: `cycle-<i>/issues.jsonl` с `created | reused | deferred | count_new`.

### 3. Решение до закрытия

Для **каждого** open issue с `Cycle-run: <run_id>` (этот прогон, все циклы 1..i):

1. Fix на `WORK_BRANCH` (never `main`). Не поднимать бюджеты / forensic timeout.
2. Re-scan только затронутые UID/panels. Post-change:
   focused pytest + §8 gates, которые задеты.
3. PR в `main` если `ALLOW_PUSH=true`. `ALLOW_MERGE=false` — не merge.
4. Close (`ALLOW_CLOSE=true`) только если acceptance виден на `origin/main`
   **или** оператор явно принял PR-head. Иначе `BLOCKED` + ссылка на PR.
5. Не закрывать BLOCKED как DONE. Не reopen уже закрытые.

Выход: `cycle-<i>/closeout.md` — таблица `issue# | verdict | SHA/PR | checks`.

## STOP (обязателен)

После шага 2 цикла `i` вычислить:

- `new_issues_i` = число **вновь созданных** issue в этом цикле
  (reused/deferred не считаются);
- `open_cycle_issues` = open GitHub issues с `Cycle-run: <run_id>`
  (включая созданные в циклах `1..i-1`).

**Остановиться немедленно**, если одновременно:

1. `new_issues_i == 0`, и
2. `open_cycle_issues == 0`.

Тогда шаг 3 этого цикла не нужен (нечего закрывать). Писать `final-summary.md`.

Иначе выполнить шаг 3, затем цикл `i+1`, пока `i < N`.

Дополнительный STOP: `N` исчерпан; invented `DASH-*`; monitoring start без
одобрения; orchestrator hard-stop; `NO_ACTIONABLE_FINDINGS` на шаге 1 **и**
`open_cycle_issues == 0`.

Если `N` исчерпан, а `open_cycle_issues > 0` — `BLOCK` в final-summary,
список оставшихся issue, не выдумывать пустые циклы.

Сессия кончилась до `N` — resume с того же `run_id` / `cycle-<i>`; не
сбрасывать ledger.

## Outputs

```text
reports/audit/dashboard-full-cycle/<run_id>/
  run.json
  cycle-<i>/inventory.md, panel-matrix.csv, findings.json,
    issues.jsonl, closeout.md, summary.md
  ledger.jsonl
  final-summary.md
```

## Final summary

| Cycle | new_issues | open_cycle_issues | P0–P1 left | PR/SHA | Gate |
| --- | --- | --- | --- | --- | --- |

Gate: `PASS` (STOP met) \| `WARN` \| `BLOCK` (N exhausted with open cycle issues).

## Success

- Шаги 1→2→3 соблюдены; STOP-условие выполнено или N исчерпан с BLOCK
- Нет открытых issues **этого** `run_id` без BLOCKED-причины при PASS
- Нет commit в `main`, нет правок `.env`, бюджеты не выросли
- `grafana-six/*` и второй sequential-run не запускались
