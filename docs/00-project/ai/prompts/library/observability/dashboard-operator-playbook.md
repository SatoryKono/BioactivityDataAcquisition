---
id: prompt.observability.dashboard-operator-playbook
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
  - SCENARIO_COUNT
  - OUTPUT_DIR
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
related_ssot:
  - AGENTS.md
  - grafana/dashboards
  - docs/03-guides/dashboards/contracts/dashboard-inventory.yaml
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/operator-ux-v2.md
  - docs/03-guides/dashboards/operator-scenarios-s1-s6.md
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Inventing panel ids or titles not in shipped JSON
  - Skipping collapsed-row children
  - Writing one generic choice for every panel
  - Treating VALID EMPTY as QUERY ERROR or UNKNOWN as OK
  - Starting monitoring unless MONITORING=true
  - Reopening #8944-#8948
tags: [observability, dashboard, grafana, operator, playbook, scenario, verification]
summary: Systematic per-panel operator playbook — question, dashboard link, analysis order, 5-10 scenarios with value-dependent choices
max_body_lines: 280
---

# BioETL — систематическая проверка дашбордов (operator playbook)

Построй **полный** playbook: каждая панель каждого shipped UID, затем
5–10 сценариев на дашборд с выбором оператора от значения панели.
Не runtime SSOT. Язык: `{{LANGUAGE}}`. Не выдумывать id/title.

## Params

| Param | Default |
| --- | --- |
| `TASK` | playbook всех семи UID: вопрос панели, связь с вопросом дашборда, маршрут, сценарии |
| `MODE` | `audit` (писать только `reports/**` + эту карточку; JSON дашбордов не менять) |
| `SCOPE` | `grafana/dashboards` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `SCENARIO_COUNT` | `8` (минимум 5, максимум 10 на UID) |
| `OUTPUT_DIR` | `reports/audit/observability-seq/<utc>-operator-playbook-<shortsha>/` |

## Вопросы дашбордов (не переименовывать)

| UID | Вопрос дашборда |
| --- | --- |
| `bioetl-control-plane-v1` | Можно ли replay/resume выбранного pipeline/run? |
| `bioetl-overview-v2` | Что требует внимания сейчас и какой first action? |
| `bioetl-runtime` | Где пайплайн заблокирован и почему? |
| `bioetl-provider-health-v2` | Какой provider нездоров и какая причина? |
| `bioetl-dq-v2` | Текущий DQ OK? Какие rejects/thresholds? |
| `bioetl-incident-v1` | Кто ranked suspect этого инцидента? |
| `bioetl-run-explorer-v1` | Какая exact-run identity и accounting? |

Связь панели с дашбордом: `answers` / `gates` / `localizes` / `handoff` /
`chrome` (nav/scope). Одна роль на панель.

## Маршрут анализа (root Y, затем expand)

Порядок = `gridPos.y`, затем `x`. Children collapsed row — только если
маршрут или сценарий велят `EXPAND_ROW`.

| UID | Последовательность (id) |
| --- | --- |
| Trust | `1000 → 9400 → 9401 → 9418 → 9416 → 906 → 891/892/893/907 → 9419 → 902 → 901 → 903 → 904 → 905 → 9412` |
| Overview | `1000 → 99 → 9603 → 214 → 215 → 9002 → 9600 → 9030 → 9009 → 9012 → 9602` |
| Runtime | `1000 → 9400 → 9401 → 9991 → 9101 → 9102 → 252 → 253 → 254 → 9992 → 9993 → 9994` |
| Provider | `1000 → 9400 → 9401 → 9002 → 9101/9102/9103 → 9104 → 9105 → 91 → 9404 → 9405` |
| DQ | `1000 → 9400 → 9401 → 9103 → 9101 → 9405 → 9404 → 220 → 221` |
| Incident | `1000 → 9400 → 9401 → 2001 → 2010 → 2020 → 2099` |
| Run Explorer | `1000 → 1 → 3010 → 3099 → 3098` |

S1–S6 из `operator-scenarios-s1-s6.md` — междашбордные hops, не замена
внутридашбордного маршрута.

## Вопрос панели

Для **каждого** id из JSON (включая children rows):

| Поле | Откуда |
| --- | --- |
| `panel_question` | title + description; не выдумывать метрику |
| `dashboard_link` | как ответ панели сужает вопрос UID |
| `when` | NOW / RANGE / RUN / WORKFLOW / GLOBAL |
| `empty_tokens` | `noValue` + description (`UNKNOWN`, `SELECT RUN`, `VALID EMPTY`, `QUERY ERROR`, `TREE_MISSING`) |

`MONITORING=false` → live значения `Not Verifiable`, не defect.

## Сценарии ({{SCENARIO_COUNT}} на UID)

Обязательный набор (лишние — только из JSON/контрактов):

1. `healthy_or_valid_empty`
2. `unknown_telemetry`
3. `warn_degraded`
4. `crit_stop`
5. `incomplete_trust_gate`
6. `select_run_sentinel` (`run_id=-`)
7. `backend_query_error`
8. `bind_tree_missing` (особенно 3010/3020/3021)
9. `selector_unknown_pipeline` (если есть `$pipeline`)
10. `now_vs_range_disagree` (если есть NOW и RANGE)

Селекторы сценария: `workflow`, `pipeline`, `run_type`, `run_id`,
`provider` — только существующие variables UID.

## Выбор оператора (на каждую панель сценария)

Enum: `STAY` | `CHANGE_SELECTOR` | `EXPAND_ROW` | `HOP_DASHBOARD` |
`CLI` | `STOP_REPLAY` | `FIX_TELEMETRY` | `TREAT_VALID_EMPTY` |
`TREAT_BIND_FAILURE` | `OPEN_RUNBOOK`.

Правила (уточнять copy панели, не спорить с ним):

| Значение / noValue | Выбор |
| --- | --- |
| OK / 0 expected | `STAY` |
| VALID EMPTY | `TREAT_VALID_EMPTY` (не hop) |
| WARN | `EXPAND_ROW` или `HOP_DASHBOARD` по CTA |
| CRIT / FAIL | `STOP_REPLAY` на Trust; иначе hop + runbook |
| UNKNOWN / TELEMETRY ABSENT | `FIX_TELEMETRY` |
| INCOMPLETE | не replay; закрыть evidence gap |
| SELECT RUN / `run_id=-` | `CHANGE_SELECTOR` на UUID с 3010/215 |
| QUERY ERROR / 503 | backend, не «пустой пайплайн» |
| TREE_MISSING / LAYOUT_UNHEALTHY | `TREAT_BIND_FAILURE` + `verify_report_bind.py` |
| First Action / Ranked Suspects row | `HOP_DASHBOARD` с сохранением vars/time |

Запрещено одно и то же действие на все панели сценария, если значения разные.

## Артефакты

```text
{{OUTPUT_DIR}}
  00-inventory.json      # uid → [panel_id…] из JSON
  01-panel-questions.md  # вопрос + dashboard_link на каждую панель
  02-operator-path.md    # маршрут по UID
  03-scenarios.md        # 5–10 сценариев × все панели маршрута
  playbook.json          # machine-readable
  report.md
```

`playbook.json` scenario row: `uid`, `scenario_id`, `selectors`,
`panel_id`, `observed_or_assumed_value`, `choice`, `next_panel_id`,
`rationale`. Coverage: каждый `panel_id` инвентаря ≥1 раз в
`01-panel-questions.md`; в каждом сценарии — все first-screen id плюс
каждый expand, который сценарий открывает.

## Done when

- [ ] 7 UID, 0 выдуманных панелей
- [ ] 5–10 сценариев на UID, у каждой затронутой панели — choice из enum
- [ ] S1–S6 hops согласованы с `operator-scenarios-s1-s6.md`
- [ ] Live gaps при `MONITORING=false` помечены NV, не FAIL
