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

Для current-status `stat`-панелей на first screen:

- `options.colorMode = background`
- explicit value mapping MUST exist for operator-facing enums:
  - `0 -> OK`
  - `1 -> WARN`
  - `2 -> CRIT`
  - `null -> UNKNOWN`

Это правило применяется к severity-adapter поверхностям, которые отвечают на
главный operator question dashboard-а. Оно не распространяется автоматически на
raw-state diagnostic surfaces с собственной доменной семантикой (`HEALTHY /
DEGRADED / FAILING`, `CLOSED / HALF-OPEN / OPEN`) или на range-evidence cards.

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

## 4.1) First-screen responsibility and panel decision matrix (обязательно)

Каждый shipped dashboard имеет ровно один основной операторский вопрос. Первый
экран должен отвечать на этот вопрос через current-status сигналы, а не через
выбранный Grafana range. Range evidence, raw counters и forensic details
помещаются ниже первого экрана или в dedicated drilldown.

| Dashboard | First-screen responsibility | Current-status rules | Selected-range evidence | Drilldown / forensic surface |
| --- | --- | --- | --- | --- |
| `bioetl-overview-v2` | Что сейчас broken/degraded и куда идти дальше? | `bioetl_l0_status`, `bioetl_l0_next_action_route`, `bioetl_l0_input_status` | collapsed `Range Evidence` row | linked L1 dashboards |
| `bioetl-runtime` | Что прямо сейчас блокирует runtime execution? | `bioetl_runtime_current_status`, `bioetl_runtime_current_blocker_reason` | failed/no-record runs, stage lag/backlog trends, shutdown intervals | Runtime detail tables, Loki/Tempo handoff |
| `bioetl-provider-health-v2` | Какой provider сейчас degraded/failing и почему? | `bioetl_provider_current_status`, `bioetl_provider_current_cause` | health-check counters, failure/degraded trends, latency/rate-limit history | provider detail panels and runbook links |
| `bioetl-dq-v2` | Каково текущее DQ состояние и первое действие? | `bioetl_dq_current_status`, `bioetl_dq_current_reason` | Bronze→Silver→Gold range flow, reject counts/rates, validation histories | `bioetl-silver-reject-explorer`, DQ diagnostics |
| `bioetl-control-plane-v1` | Можно ли доверять control plane и безопасно replay/resume? | replay/checkpoint/manifest trust summary rules | manifest/ledger/checkpoint/audit histories | replay safety diagnostics and runbooks |

Decision matrix:

| Panel class | Belongs on first screen? | Query contract | Naming contract |
| --- | --- | --- | --- |
| Current status / current reason | Yes | Fixed current windows or recording rules; MUST NOT use `$__range` | `Monitor ...` or `Inspect ...` |
| Next action / route | Yes | Low-cardinality route/action rules; preserve `UNKNOWN` when data is missing | `Next Action`, `First Action`, or `Inspect ...` |
| Selected-range count/rate/trend | No, except compact L0 context | MUST use `$__range`, `$__interval`, or explicit range wording | `Track ... in Range` or description says selected range |
| Raw counter / histogram / latency evidence | No | Preserve no-data unless zero is semantically valid | `Track ...` |
| Forensic row/table/details | No | May carry scoped IDs only in dedicated explorer surfaces | `Inspect ...` or `Investigate ...` |

Normative rules:
- First-screen current-status panels MUST NOT use `$__range`.
- Range panels MUST include selected-range wording in title or description.
- Top-level `gridPos` rectangles in a shipped dashboard MUST NOT overlap;
  navigation, scope, first-action, current-status, range evidence, and collapsed
  rows must occupy explicit non-overlapping grid bands.
- Top-level root layout MUST NOT leave unexplained empty row gaps between
  adjacent bands; if a dashboard intentionally adds vertical breathing room, the
  exception must be justified in the dashboard audit or docs mirror.
- `or vector(0)` is allowed only for event-count panels where missing series
  means zero events; status panels preserve `UNKNOWN`.
- Deep details (`run_id`, `payload_hash`, record-level tables) MUST NOT appear
  on first-screen status rows.

## 4.2) Layout grammar by dashboard role (обязательно)

Shipped dashboards do not share identical geometry, but they MUST share the
same answer-first reading order.

| Dashboard role | Shipped dashboards | Above-the-fold responsibility | Lower bands |
| --- | --- | --- | --- |
| L0 answer-first hub | `bioetl-overview-v2` | current answer, next route, bounded mirrors | historical context, routing aids, collapsed diagnostics |
| L1/L2 triage | `bioetl-runtime`, `bioetl-control-plane-v1`, `bioetl-provider-health-v2`, `bioetl-dq-v2` | current verdict, first action, causes, trust markers | selected-range evidence, collapsed diagnostics |
| Selected-range operational evidence | `bioetl-workflow-overview` | selected-range operational verdict and immediate fallout | lower evidence bands, optional collapsed diagnostics |
| Forensic explorer | `bioetl-silver-reject-explorer` | scope semantics, no-data guidance, bounded summary | row-level browsing, record details, forensic tables |

Normative rules:
- Every shipped dashboard MUST answer its primary operator question before the
  first evidence-heavy row.
- Historical or selected-range evidence MUST NOT visually precede current-state
  answer surfaces on L0/L1/L2 dashboards.
- Forensic explorer surfaces are exempt from Prometheus-style symmetry, but
  they still MUST keep scope semantics and first action above row-level detail.

## 4.3) Visibility tiers and collapse policy (обязательно)

Every shipped dashboard should classify panels into one of four tiers:

- `Tier 1`: always-visible answer surface
- `Tier 2`: always-visible supporting current context
- `Tier 3`: below-fold selected-range evidence
- `Tier 4`: collapsed diagnostics, raw evidence, tracing-only detail, rare
  forensic breakdowns

Normative rules:
- `Tier 1` MUST remain visible without extra clicks and MUST contain current
  status / verdict, first action, or current causes needed for first-pass
  triage.
- `Tier 2` MAY add KPI context, trust markers, or bounded mirrors, but MUST
  support `Tier 1` rather than compete with it.
- `Tier 3` belongs below the answer bands unless the dashboard role is itself
  selected-range evidence.
- `Tier 4` SHOULD be collapsed when it is tracing-only, raw, verbose, or not
  required for first-pass operator triage.
- The only copy of a critical signal MUST NOT live exclusively inside a
  collapsed row.

## 4.4) Datasource trust semantics (обязательно)

Shipped dashboards use more than one datasource class and MUST not flatten
their trust semantics into a single generic `No data` story.

Datasource categories:

- **Primary operator datasource**: Prometheus for current verdict, current
  causes, selected-range evidence, and KPI panels.
- **Secondary forensic datasource**: Quarantine Explorer HTTP API for row-level
  reject exploration and payload/detail inspection.
- **Investigative handoff surfaces**: Loki / Tempo through `Explore Logs` and
  `Explore Traces`; these are handoffs, not shipped dashboards.

Normative rules:
- Prometheus current-status and current-cause panels MUST remain fail-closed:
  preserve `UNKNOWN`, MUST NOT use `or vector(0)`, and MUST NOT silently
  convert missing telemetry into healthy state.
- `or vector(0)` remains valid only for true zero-event counters where missing
  series semantically means zero events.
- A dashboard MUST add an explicit trust marker only when the operator could
  otherwise confuse empty scope, telemetry gap, or backend failure.
- HTTP-backed forensic surfaces MUST distinguish:
  - valid scope with zero matching rows
  - invalid or unsupported filter chain
  - backend / datasource query failure
- `Silver Reject Explorer` first-screen copy and detail descriptions MUST
  explain this distinction before the operator treats an empty table as OK.

## 4.5) Missing-data semantics by panel class (обязательно)

Не существует одного универсального `noValue` текста для всех dashboards.
Shipped surfaces MUST различать valid zero, empty result, `UNKNOWN` и
datasource/query failure по роли панели.

### 4.5.1 Current-status / current-cause panels

- `null` MUST рендериться как `UNKNOWN`.
- `or vector(0)` запрещён.
- Missing telemetry MUST оставаться fail-closed, а не превращаться в synthetic
  healthy state.

### 4.5.2 Zero-valid event counters

- `or vector(0)` допустим только тогда, когда отсутствие серии действительно
  означает ноль событий.
- Это MUST быть видно либо в query, либо в description.

### 4.5.3 Timeseries / latency / histogram evidence

- `No data` остаётся диагностическим сигналом.
- Нельзя синтетически подменять отсутствие samples на `0s`, `0ms` или похожий
  healthy-looking value.

### 4.5.4 Forensic tables and HTTP-backed explorer surfaces

- Valid empty result SHOULD описываться как empty result / no matching rows.
- Unsupported filter chain, empty denominator, invalid scope или backend
  failure MUST отличаться от empty result.
- `Silver Reject Explorer` MUST объяснять это distinction в first-screen CTA и
  в detail-table descriptions.

### 4.5.5 Telemetry-gap / trust-marker policy

- Trust-marker panels обязательны только там, где без них оператор не может
  безопасно интерпретировать first-screen verdict.
- Они required для surfaces наподобие `Runtime` и `Control Plane`, где zero
  counters без telemetry health могут вводить в заблуждение.
- Они не являются blanket requirement для всех dashboards.

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
- отсутствие top-level `gridPos` overlaps в
  `tests/integration/test_grafana_dashboard_first_screen_contract.py`
- `background` colorMode + explicit `OK/WARN/CRIT` value mappings для
  designated current-status severity stat panels

## 7) UI-лексика навигации (обязательно)

Источник фиксированного словаря для `links[].title`: `docs/03-guides/dashboards/navigation-contract.md`.

Правила:
- Названия top-level ссылок MUST совпадать с каноническими строками из navigation contract (например: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `Silver Reject Explorer`).
- Explore-ссылки MUST использовать короткие названия: `Explore Logs` и `Explore Traces`.
- Формулировки вида `Back to Overview`, `5. Control Plane`, `6. Workflow Overview`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)`, `Next Recommended Drilldown` считаются legacy-лексикой и не допускаются в shipped top navigation.

### 7.1) Link title style-guide: Back / Open / Investigate

Используй единый шаблон для операторских ссылок:

- `Back to <Dashboard>` — только для возврата на предыдущий L0 уровень.
- `Open <Target>` — переход в соседний dashboard или внешний runbook без forensic-контекста.
- `Investigate <Target>` — переход в forensic/deep-dive surface (например, reject explorer, incident drilldown).

Норматив:
- Для top-level `links[]` в `grafana/dashboards/*.json` MUST использоваться только эти глаголы для action-link лексики (`Back`, `Open`, `Investigate`), кроме канонических имен dashboard (`2. Runtime`, `3. Provider Health`, и т.д.).
- Для `options.dataLinks` в критичных панелях предпочтителен `Open ...`; `Investigate ...` допустим для incident/deep-dive панелей.

### 7.2) Scope reset suffix в tooltip (обязательно)

Если link меняет scope (например, принудительно ставит `var-pipeline=unknown`, сбрасывает provider/adapter или stage, либо сбрасывает `var-run_type` на `All`), tooltip MUST содержать явный suffix:

- `Scope reset: ...`

Рекомендуемый шаблон:

- `Cross-scope handoff ... Scope reset: pipeline=unknown, run_type=All; provider/adapter not transferred.`

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
