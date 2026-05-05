# Dashboard Design System (BioETL)

Дата актуализации: **2026-05-03**
Источник истины: `grafana/dashboards/*.json`

## 1) Единая семантика статусов OK/WARN/CRIT/UNKNOWN (обязательно)

Для status-панелей (`stat`/`gauge`) применяется фиксированная палитра:

- **OK** → `green`
- **WARN** → `orange`
- **CRIT** → `red`
- **UNKNOWN** → `gray`

`UNKNOWN` обязателен как явное отображение no-data/null через mapping:
- `null` → текст `UNKNOWN` + цвет `gray`.

### 1.1 Canonical mapping: L0 vs diagnostic dashboards

| Dashboard surface | Numeric range | Canonical status term | Visualization color |
| --- | --- | --- | --- |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `0` | `OK` | `green` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `1` | `WARN` | `orange` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `>=2` | `CRIT` | `red` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `null` | `UNKNOWN` | `gray` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `<1` | `OK` *(alias `HEALTHY` optional)* | `green` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=1 and <2` | `WARN` *(alias `DEGRADED` optional)* | `orange` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=2` | `CRIT` *(alias `BROKEN` optional)* | `red` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `null` / no data | `UNKNOWN` | `gray` |

Норматив:
- В **L0 operator dashboards** MUST использоваться только термины `OK/WARN/CRIT/UNKNOWN`.
- Термины `DEGRADED/BROKEN/HEALTHY` допускаются только в диагностических deep-dive поверхностях и MUST быть явно привязаны к этой таблице.
- Если в диагностическом UI используются alias-термины, в description MUST присутствовать строка вида `Alias mapping: DEGRADED=WARN, BROKEN=CRIT`.

## 2) Единые threshold ranges (обязательно)

### 2.1 Stat/Gauge

Для всех status-панелей:

- `fieldConfig.defaults.color.mode = thresholds`
- `fieldConfig.defaults.thresholds.mode = absolute`
- `fieldConfig.defaults.thresholds.steps`:
  1. `{ "color": "green", "value": null }`
  2. `{ "color": "orange", "value": 1 }`
  3. `{ "color": "red", "value": 2 }`

Нормативная интерпретация:

- `0` → OK
- `1` → WARN
- `>=2` → CRIT
- `null` → UNKNOWN

### 2.2 Time-series

Для time-series, визуализирующих те же статусы, диапазоны MUST совпадать семантически:

- OK: `< 1`
- DEGRADED: `>= 1 and < 2`
- BROKEN: `>= 2`
- UNKNOWN: отсутствие данных/NaN/null отображается как unknown-состояние, а не как OK.

## 3) Единый стиль заголовков и описаний панелей (обязательно)

### 3.1 Заголовок (action-first)

Шаблон:

`<Action Verb>: <Object/Signal> [<Window>]`

Примеры:
- `Monitor: Runtime Failure Rate [24h]`
- `Inspect: Provider Retry Saturation [1h]`
- `Track: Latest Successful Data Timestamp`

Требование: все новые панели MUST использовать action-first заголовки с глаголом в начале (`Monitor`, `Inspect`, `Track`, `Compare`, `Review`).

### 3.2 Description

Шаблон:

1. Что измеряется (1 предложение)
2. Как интерпретировать `OK/WARN/CRIT/UNKNOWN`
3. Если применимо — ссылка на runbook/drilldown

Пример структуры:

- `Measures ...`
- `Status mapping: 0=OK, 1=WARN, >=2=CRIT, null=UNKNOWN.`
- `Use <dashboard/link> for drilldown.`

## 4) Правило no-data/unknown (обязательно)

- Нельзя молча трактовать no-data как OK для status-панелей.
- Если no-data действительно эквивалентно нулевому событию, это должно быть отражено в query явно (`... or vector(0)`) и подтверждено в description.
- Во всех остальных случаях no-data должен остаться `UNKNOWN`.

## 5) Единый unit/decimals для схожих KPI (обязательно)

- Для счётчиков событий (`... Missing`, `... Incompatibilities`, `... Failures`) использовать `unit=short`, `decimals=0`.
- Для timestamp KPI (`Latest Successful Data Timestamp` и аналогичные) использовать `unit=dateTimeAsIso`, `decimals=0`.
- Для долей/процентов (`... Rate`, `... Ratio`) использовать единый unit внутри dashboard-семейства (`percentunit` или `percent`) и согласованный `decimals` (обычно `0` или `2`).
- Схожий KPI в разных dashboards MUST иметь одинаковую пару `unit/decimals`.

## 6) QA Gate

Базовая автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
```

Проверка валидирует:

- color mode = `thresholds`
- стандартизованные threshold steps
- обязательный `UNKNOWN` mapping для `null`

## 7) UI-лексика навигации (обязательно)

Источник фиксированного словаря для `links[].title`: `docs/03-guides/dashboards/navigation-contract.md`.

Правила:
- Названия top-level ссылок MUST совпадать с каноническими строками из navigation contract (например: `Back to Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Silver Reject Explorer`, `5. Control Plane`, `6. Workflow Overview`).
- Explore-ссылки MUST использовать короткие названия: `Explore Logs` и `Explore Traces`.
- Формулировки вида `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)`, `Next Recommended Drilldown` считаются legacy-лексикой и не допускаются в shipped dashboards.

### 7.1) Link title style-guide: Back / Open / Investigate

Используй единый шаблон для операторских ссылок:

- `Back to <Dashboard>` — только для возврата на предыдущий L0 уровень.
- `Open <Target>` — переход в соседний dashboard или внешний runbook без forensic-контекста.
- `Investigate <Target>` — переход в forensic/deep-dive surface (например, reject explorer, incident drilldown).

Норматив:
- Для top-level `links[]` в `grafana/dashboards/*.json` MUST использоваться только эти глаголы для action-link лексики (`Back`, `Open`, `Investigate`), кроме канонических имен dashboard (`2. Runtime`, `3. Provider Health`, и т.д.).
- Для `options.dataLinks` в критичных панелях предпочтителен `Open ...`; `Investigate ...` допустим для incident/deep-dive панелей.

### 7.2) Scope reset suffix в tooltip (обязательно)

Если link меняет scope (например, принудительно ставит `var-pipeline=All`, `var-run_type=All`, сбрасывает provider/adapter или stage), tooltip MUST содержать явный suffix:

- `Scope reset: ...`

Рекомендуемый шаблон:

- `Cross-scope handoff ... Scope reset: pipeline=All, run_type=All; provider/adapter not transferred.`

Если scope не меняется, используй нейтральный tooltip:

- `Preserves selected scope and time range.`

## 7.1) L1 layout rule: answer-first above fold (обязательно)

Для L1 control-plane dashboards первый экран (above fold) MUST отвечать на
вопрос оператора без прокрутки:

- ровно один верхний triage-row с **3–5 KPI**;
- в этом же ряду MUST быть **ровно одна** явная панель next-step/drilldown;
- панели глубокой диагностики MUST быть вынесены в secondary collapsed rows с
  заголовками по incident-сценариям (`Incident Drilldown: ...`).

Нельзя дублировать next-step call-to-action в нескольких L1 панелях одного
dashboard: для первичной навигации используется единая точка входа.

## 8) JSON invariant: timezone (обязательно)

Для всех shipped dashboards в `grafana/dashboards/*.json` применяется единый JSON-invariant:

- корневое поле `timezone` MUST быть `"browser"`.

Пример:

```json
{
  "timezone": "browser"
}
```


## 9) Actionable links for critical panels (обязательно)

Для критичных (`P1`/`P2`) operator panels типов `stat`/`gauge`/`table` MUST быть минимум один actionable `options.dataLinks` entry.

Минимальный контракт:
- `options.dataLinks` содержит хотя бы один объект;
- `title` начинается с шаблона `Open <target>`;
- `url` ведёт в целевой dashboard/runbook для drilldown.

Пример:

```json
"options": {
  "dataLinks": [
    {
      "title": "Open bioetl-runtime",
      "url": "/d/bioetl-runtime/bioetl-runtime",
      "targetBlank": false
    }
  ]
}
```
