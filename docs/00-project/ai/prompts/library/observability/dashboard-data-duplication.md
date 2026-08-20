---
id: prompt.observability.dashboard-data-duplication
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
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/dashboard-requirements-audit.md
  - fragments/project-requirements-audit.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/03-guides/dashboards/contracts/layout-budgets.yaml
  - docs/03-guides/dashboards/verdict-ontology.md
  - grafana/dashboards
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Inventing panels, UIDs, metrics, or DASH-* IDs
  - Calling summary/detail (fold vs collapsed row) a defect without same-row proof
  - Removing DASH-FIT-003 answer panels or raising first_screen_max_panels
  - Putting limit=20 / unfiltered tables on the first window to "dedupe"
  - Treating workflow vs pipeline indexes as duplicates
  - Data FAIL from a screenshot
  - Starting monitoring unless MONITORING=true
  - One GitHub issue per cosmetic title when the root cause is a shared endpoint
tags: [observability, dashboard, grafana, duplication, panels, audit, operator]
summary: Sequential per-dashboard panel data audit — find intra-dashboard duplicates, plan exclusions without breaking FIT
max_body_lines: 240
---

# BioETL — дубли данных внутри дашборда (последовательный проход 0–6)

Последовательно изучи **каждый** из семи shipped UID. Для **каждой** панели
зафиксируй, какие данные она показывает. Выдели дубли **внутри одного**
дашборда. Предложи план исключения панелей с дублирующими данными.

Не runtime SSOT. Язык: `{{LANGUAGE}}`. Shipped JSON = structure SSOT.
`MONITORING={{MONITORING}}` (default false): live query не обязателен;
классифицируй по URL / PromQL / `root_selector` / transformations.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `SCOPE` | `grafana/dashboards` (all seven UID) or one uid |
| `LANGUAGE` | `ru` |
| `MODE` | `audit` (`audit` \| `propose-patches`) |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `WORK_BRANCH` | `fix/dash-dedupe-<shortsha>` (never main) |

Windows: `.\.venv-win\Scripts\python.exe`. Skill: **observability-dashboard**.

## Порядок дашбордов (обязательный)

Не прыгать. После каждого UID — таблица панелей + кластеры дублей +
do-not-remove. Затем следующий UID.

| # | UID | Answer panel (`DASH-FIT-003`) |
| ---: | --- | --- |
| 0 | `bioetl-control-plane-v1` | `9401` Monitor Replay Readiness |
| 1 | `bioetl-overview-v2` | `214` + `215` (не заменять; `9603` = SELECTED RUN context) |
| 2 | `bioetl-runtime` | `9401` Monitor Pipeline Status |
| 3 | `bioetl-provider-health-v2` | `9101` Monitor Fleet Severity |
| 4 | `bioetl-dq-v2` | `9401` Monitor Current DQ Status |
| 5 | `bioetl-incident-v1` | `2010` Inspect Ranked Suspects |
| 6 | `bioetl-run-explorer-v1` | `9402` Inspect Run Identity (`3010` = empty-selection utility) |

## Метод на каждый UID

### 1. Inventory панелей

Из JSON (и вложенных `row.panels`). Колонки:

`id | title | type | band | datasource | endpoint_or_expr | root_selector | transform | unique_fields`

`band`: `first_window` (`y < 18`) \| `first_load` (`y < 28`) \| `below` \| `row`.

Для Infinity: `url` + `root_selector` + `filterByValue` / `limit` / `organize`.
Для PromQL: metric names + labels + `$__range` vs CURRENT. Не изобретать series.

Text-панели: это **copy**, не данные — помечай `copy-only`.

### 2. Классификация дубля (обязательная таксономия)

Один кластер = один `endpoint_id` или один PromQL root-cause.

| Класс | Критерий | Типичное решение |
| --- | --- | --- |
| `subset` | тот же URL/expr; Grafana filter/limit режет строки | summary на fold + full в collapsed row — **оставить**, если разные `band` |
| `same-row-subset` | subset и **оба** в одном collapsed row / одном fold | **кандидат на удаление** subset |
| `superset-index` | тот же list-endpoint, больший `limit` | не удалять first-window cap (`DASH-FIT-005`); full-list только below fold |
| `same-document-slice` | один JSON, разные `root_selector` (funnel vs reasons vs artifacts) | **не** дубль UI; опционально кэш HTTP |
| `semantic-overlap` | разные endpoints, похожие KPI (funnel vs processed-records CURRENT) | не сливать без доказательства 1:1 полей |
| `copy-only` | text без query, повторяет соседнюю таблицу | удалить или влить в существующий copy |
| `not-duplicate` | другой resource (pipeline vs workflow index; CURRENT vs RANGE; fleet vs selected) | не трогать |
| `http-fanout` | N одинаковых GET одного документа | не удалять панели; отдельно оптимизировать scrape |

`DASH-QUERY-001`: near-duplicate PromQL консолидировать или явно обосновать роль.

### 3. Защищённые панели (не предлагать удаление)

- Answer panel UID (`DASH-FIT-003`).
- First-window table с `max_rows` в `layout-budgets.yaml` (`DASH-FIT-005`).
- Nav bus `id=1000` / Navigate*.
- Панели с **уникальными** полями, которых нет в subset.

Запрещено «дедупить», вынося `limit=20` / unfiltered identity на first window
или поднимая `first_screen_max_panels`.

### 4. План исключения (на UID)

Волны:

| Волна | Что | Пример |
| --- | --- | --- |
| 1 | `copy-only` без query | text, который только отсылает к таблице рядом |
| 2 | `same-row-subset` | 4-row teaser и full table в одном `row` |
| 3 | обоснованный отказ удалять `subset`/`superset-index` с разным `band` | fold last-4 vs details last-20 |
| 4 | не сливать `semantic-overlap` / `same-document-slice` без контракта | funnel ≠ CURRENT gauges |

Каждый кандидат: `id`, класс, что остаётся, какие контракты править
(`run-explorer-http-catalog.yaml`, panel-docs, inventory `panel_count`,
`layout-budgets.yaml`), риск, гейты.

## Выход

`reports/audit/grafana-panels/data-duplication/<uid>.md` + сводный
`findings.json` (`requirement_id` = `DASH-QUERY-001` / `DASH-FIRST-002` /
`DASH-FIT-003` / `GAP`).

Сводка на UID:

```text
uid | panels | subset pairs | same-row-subset | copy-only | remove | keep-as-disclosure | do-not-remove
```

`MODE=propose-patches`: только волны 1–2, минимальный JSON, без роста бюджетов.
`ALLOW_ISSUE_WRITE=true`: один issue на кластер endpoint, не на каждую панель.

## Stop

Пустой SCOPE. Выдуманные панели/метрики. Удаление answer panel. Data FAIL со
скриншота. Monitoring без `MONITORING=true`.

## Success

- Семь UID (или SCOPE) пройдены по порядку
- У каждой data-bearing панели есть endpoint/expr + класс
- План исключения не ломает FIT-003 / FIT-005
- `surface_score` 0–3; cap 1 если предложен снос answer panel
