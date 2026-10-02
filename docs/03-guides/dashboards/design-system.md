# Dashboard Design System (BioETL)

Дата актуализации: **2026-08-14**
Источник истины: `grafana/dashboards/*.json`

Normative presentation floors and measurement rules are owned by
[`DASHBOARD_REQUIREMENTS.md`](../../01-requirements/DASHBOARD_REQUIREMENTS.md).
This guide explains their application; archived DUX typography floors do not
override the active requirements contract.

**Dashboard System 2.0:** operator first-screen contract and verdict model live in
[operator-ux-v2.md](operator-ux-v2.md) and [verdict-ontology.md](verdict-ontology.md).
Prose-first first screens (giant Provenance / multi-paragraph First Action without
evidence) are **deprecated**. Evidence strip + status + ≤4 CTAs is required.

## 1) Единая семантика состояний (обязательно)

Для status-панелей (`stat`/`gauge`) применяется фиксированная палитра:

- **OK** → `green`
- **WARN** → `orange`
- **CRIT** → `red`
- **UNKNOWN** → neutral (`gray` background; theme `text` foreground for text-only cards)
- **INCOMPLETE** → neutral (`gray` background; theme `text` foreground for text-only cards; required evidence is missing or stale; never OK)
- **ERROR** → `red` for an explicit query/datasource/backend failure

`UNKNOWN` обязателен как явное отображение no-data/null через mapping:
- `null` → текст `UNKNOWN` + нейтральный цвет: `gray` для фона,
  theme `text` для карточек с `colorMode=value`. Тёмно-серый текст на тёмном
  фоне не допускается; нейтральный цвет не означает статус OK.

Terminal-state vocabulary is role-aware:

- `VALID EMPTY` / `valid-empty` — query completed and the selected scope has
  zero matching rows/events; neutral gray, with the next action in panel copy.
- `TELEMETRY ABSENT` — required metric family is absent; neutral gray and a
  scrape/target action. On headline trust gates this resolves to `INCOMPLETE`.
- `N/A` — the signal is not applicable to the selected lifecycle/scope; neutral
  gray and never a healthy verdict.
- `LOADING` — transient only. It MUST NOT remain in accepted render evidence.
- A blank panel body is not a state and MUST fail reproducible capture.

### 1.1 Canonical mapping: typed workflow and diagnostic states

Approved five-dashboard cutover: numeric encodings belong to their metric families,
not to a dashboard title. Never apply an older L0 encoding to typed workflow status.

| Evidence | Value | Meaning | Color |
| --- | --- | --- | --- |
| Incident CURRENT workflow/domain priority | `0` | `OK` | `green` |
| Incident CURRENT workflow/domain priority | `1` / null | `UNKNOWN` | `gray` |
| Incident CURRENT workflow/domain priority | `2` | `WARN` | `orange` |
| Incident CURRENT workflow/domain priority | `3` | `CRIT` | `red` |
| Legacy diagnostic severity families | `0`, `1`, `>=2`, null | `OK`, `WARN`, `CRIT`, `UNKNOWN` | green, orange, red, gray |
| Saved exact replay | `READY`, `INSUFFICIENT`, `BLOCKED` | Ready, insufficient evidence, blocked | green, orange, red |
| Saved exact replay | `UNKNOWN`, `INCOMPLETE`, `UNSUPPORTED` | No authorization to replay | gray |

Saved processing, Trust and replay readiness remain distinct. HTTP `QUERY ERROR`
is a failed request; `SELECT RUN` is missing selection. Neither becomes `READY`.
Diagnostic aliases require explicit `Alias mapping: DEGRADED=WARN, BROKEN=CRIT`.

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
- `3` → `INCOMPLETE` only on explicitly documented trust-gated panels

### 2.2 Time-series

Для time-series, визуализирующих те же статусы, диапазоны MUST совпадать семантически:

- OK: `< 1`
- DEGRADED: `>= 1 and < 2`
- BROKEN: `>= 2`
- UNKNOWN: отсутствие данных/NaN/null отображается как unknown-состояние, а не как OK.

### 2.3 Panel-type visualization standards (role-aware)

Dashboard panel visualization settings are standardized by panel role, not by a
blanket rule for every plugin type.

| Panel role | Required visualization settings |
| --- | --- |
| Current-status `stat` | `fieldConfig.defaults.color.mode=thresholds`; `options.colorMode=background` for designated first-screen severity cards; `options.textMode=value_and_name`; `options.text.valueSize=20` and `titleSize=14` so UNKNOWN is compact text-on-fill, not a full-panel glyph; `null -> UNKNOWN` mapping where the panel is fail-closed. |
| Selected-range trend `stat` | `options.colorMode=value`; `options.graphMode=area` is allowed only in the first window, otherwise `none`; threshold colors must match the measured operator risk. |
| Selected-range count `stat` | `options.colorMode=value`; `options.graphMode=none`; `or vector(0)` only when missing series means zero events. |
| Percentage, score, latency, or duration `gauge` | `options.showThresholdMarkers=true`; `options.showThresholdLabels=false` unless a panel-specific exception is documented with operator rationale. |
| Status or route `table` column | On the first window, `custom.cellOptions.type=color-background` MAY be used **only via field override** for the status/Value field. In additional row groups it MUST be `color-text` or neutral `auto`. |
| Data or forensic `table` | Use `custom.cellOptions.type=auto` as the table default when an explicit default is configured; datasource/plugin defaults are allowed for HTTP-backed forensic tables. |

**Forbidden:** table-wide default `color-background` without field overrides (paints Time/name/pipeline as severity).
| Comparative or multi-series `timeseries` | `options.tooltip.mode=multi`; `options.tooltip.sort=desc`. |
| Scalar trend `timeseries` | `options.tooltip.mode=single`; `options.tooltip.sort=none` or omitted. |

Allowed table `custom.cellOptions.type` values are `auto`, `color-background`,
and `color-text`; `color-background` is confined to the first window by
`REQ-DASH-003`. Introducing a new table cell option type requires updating
`scripts.engineering.qa check-dashboard-visual-semantics` and this design
system in the same change.

Implementation note: scalar trend exceptions are explicit, because panels such
as volume-weighted DQ score trends and L0 mirror status trends are easier to
read with single-point hover behavior. Do not apply `multi/desc` to every
timeseries without checking whether the panel compares multiple series.

## 3) Единый стиль заголовков и описаний панелей (обязательно)

### 3.1 Заголовок (action-first)

Шаблон:

`<Action Verb>: <Object/Signal> [<Window>]`

Примеры:
- `Monitor: Runtime Failure Rate [24h]`
- `Inspect: Provider Retry Saturation [1h]`
- `Track: Latest Successful Data Timestamp`

Требование: все новые панели MUST использовать action-first заголовки с глаголом в начале.

Канонический набор глаголов (action-first): `Monitor`, `Inspect`, `Track`, `Compare`,
`Review`, `Investigate` (последний — из decision matrix §4.1).

Исключения из action-first (глагол не требуется):
- `type:"row"` — заголовки-разделители;
- `type:"text"` — навигация и пояснительные/CTA-панели;
- shell-панели общего контекста §4.1.1: `Status`, `ID`, `Processed Records`.

Разбор для автоматической проверки (`DASH-COPY-003`) MUST быть colon-tolerant: и
`Monitor: Foo [24h]`, и `Monitor Foo` считаются валидными (первое слово до пробела/двоеточия).

`DASH-COPY-003` is exclusive for non-row, non-text, non-shell content panels.
Text/row/shell titles MAY keep `Navigate` / `Understand` / `Start` / `Assess` /
`Explain` / `Continue`. Former pending data-panel titles were renamed to
`Inspect Recent Runs (last 10)` and `Inspect Identity Values`.

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

Shared headline precedence is fail-closed:
`ERROR > INCOMPLETE/UNKNOWN > CRIT > WARN > OK`. `ERROR` owns an explicit
query/datasource/backend failure; `INCOMPLETE` or `UNKNOWN` owns the verdict
when required evidence cannot support a truthful business-severity decision.
Only complete evidence may resolve to `CRIT`, `WARN`, or `OK`. Presentation
colors never override this ordering.

## 4.1) First-screen responsibility and panel decision matrix (обязательно)

The approved 2026-10-02 cutover ships five dashboards. The first screen answers
its owner's question from the appropriate evidence scope. Saved assessments never
borrow a CURRENT or TIME RANGE verdict. First-window height remains 18 grid units;
all existing numeric layout, typography and coverage budgets remain unchanged.

| Dashboard | First-screen responsibility | Data source | Lower evidence |
| --- | --- | --- | --- |
| `bioetl-run-explorer-v1` | Browse the last 10 launches and select a full Run ID | Ops HTTP disk-backed index, independent of dashboard time range | Row passports, Report, and exact-run handoffs |
| `bioetl-overview-v2` | Saved overall/domain assessment, processing, Trust, and identity | One selected-run-status response, reused by summary and headline | Saved Provider Evidence, stages, and DQ canvas |
| `bioetl-control-plane-v1` | Exact replay readiness and all checks for selected Run ID | Ops HTTP replay_readiness / replay_checks | All identity anchors, Trust reasons, manifest, lineage, retention and checkpoint |
| `bioetl-dq-v2` | Saved DQ assessment and run identity | Ops HTTP selected-run-status / identity-table | Full-width saved stage/outcome accounting and saved validation |
| `bioetl-incident-v1` | CURRENT scoped workflow verdict plus GLOBAL ranked suspects and alerts | Prometheus typed workflow and incident rules | Collapsed runtime, provider and control-plane fleet/range evidence |

`bioetl-runtime` and `bioetl-provider-health-v2` are retired standalone UIDs.
Provider Evidence uses the selected Run ID on Overview; live provider suspects
stay on Incident. Loki/Tempo/Explore surfaces remain removed.

| Panel class | Placement and query contract |
| --- | --- |
| CURRENT status / cause | Incident; fixed current rules, never `$__range` or a Run ID label |
| Saved verdict / next action | Owner's first screen; preserve exact UUID and `UNKNOWN` |
| Selected-range count/rate/trend | Collapsed Incident evidence; explicit TIME RANGE scope |
| Raw counter / histogram / latency | Preserve absence separately from measured zero |
| Forensic table | Below fold or collapsed; full values remain inspectable |

Required metric families remain available on Incident, including
`bioetl_runtime_current_status_trusted`, `bioetl_provider_current_status`, and
`bioetl_dq_current_status`. These do not prove one saved run healthy.

Normative rules:

- Root grid rectangles MUST NOT overlap or leave unexplained gaps.
- Status/Trust/replay panels MUST NOT fabricate a zero with `or vector(0)`.
- Range evidence MUST name its scope; a historical zero is not current recovery.
- Exact Run ID and identity anchors use HTTP, never Prometheus labels.
- DQ freshness thresholds remain WARN `24h`, CRIT `72h` for matching metric families.
- Saved Provider Evidence preserves cached Bronze (`Performed=No`, `Result=—`),
  UNKNOWN, valid empty and request failure without a live-health claim.

### 4.1.1 Shared operator context shell

Each owner shows scope and selection; panel IDs are local to that dashboard.
Overview uses `99`, Replay Readiness/DQ/Incident use `9400`; Run Explorer uses `1`.
Incident `9401` is CURRENT; Overview `9604` reuses saved domain response `9002`.
DQ `9406` is saved assessment. There is no mandatory duplicate Status/ID/Records
shell on every dashboard.

- Run ID options use the local `/ops/control-plane/filter-options` catalog.
  Coherent tuple defaults belong to `/ops/control-plane/selector-context`.
- Overview `9300` shows five parameters: full UUID, Pipeline, Run Type, Started
  with saved UTC offset, and total duration. Full values remain inspectable.
- DQ `9403` owns saved accounting: parameter, count in, count out, percentage.
  Silver filtered, quarantined and deduplicated outcomes are distinct; Gold
  exclusion is distinct from quarantine. Missing denominators stay N/A.
  Skipped rows are hidden; recorded zero outcomes remain measured zeros.
- Overview `9603` separates processing (`Result`) and saved `Trust`. Trust is
  not replay readiness. Missing archive stays `INCOMPLETE` / `No verified archive`.
- All Replay Checks and provider evidence rows remain available through pagination.
  Finite first-window projections must retain their declared complete row set.

## 4.2) Layout grammar by dashboard role (обязательно)

| Role | Owner | Above fold | Lower bands |
| --- | --- | --- | --- |
| L0 answer-first hub for saved assessment | Run Overview | Assessment, domains, identity | Saved provider, stages and quality |
| Replay decision | Replay Readiness | Readiness and all checks | Identity / Trust / validation |
| Saved DQ assessment | Data Quality | Assessment and identity | Full stage accounting and validation |
| Current triage | Incident Workspace | CURRENT scope, GLOBAL suspects and alerts | Collapsed fleet/range diagnostics |
| Forensic explorer / launch catalog | Run Explorer | Last 10 launches and row actions | Linked saved evidence |

## 4.3) Visibility tiers and collapse policy (обязательно)

- `Tier 1`: always-visible answer, scope and next action.
- `Tier 2`: supporting identity or bounded assessment projection.
- `Tier 3`: below-fold saved evidence or range evidence clearly marked by scope.
- `Tier 4`: collapsed validation, forensic detail or fleet diagnostics.

A saved-run owner need not show a CURRENT verdict. Incident fleet evidence never
claims that its Run ID selector filtered Prometheus. Manifest/lineage/retention
and resume/checkpoint rows stay collapsed; root saved evidence may remain visible
below fold. Tables preserve all evidence through pagination or a finite declared
projection, with no clipping of required values or UUIDs. Full UUID inspection
is valid above fold; raw record dumps and hashes belong in forensic detail.

## 4.4) Datasource trust semantics (обязательно)

Shipped dashboards use more than one datasource class and MUST not flatten
their trust semantics into a single generic `No data` story.

Datasource categories:

- **Primary operator datasource**: Prometheus for current verdict, current
  causes, selected-range evidence, and KPI panels.
- **Secondary forensic datasource**: BioETL Ops HTTP HTTP API for row-level
  reject exploration and payload/detail inspection.
- **Removed investigative handoffs (2026-07-23)**: do **not** ship Loki/Tempo
  `Explore Logs` / `Explore Traces`. Use Prometheus + file logs + CLI forensics.

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
- HTTP forensic / CLI empty-result copy MUST explain this distinction before
  the operator treats an empty table as OK (`bioetl quarantine inspect`).

## 4.5) Missing-data semantics by panel class (обязательно)

Не существует одного универсального `noValue` текста для всех dashboards.
Shipped surfaces MUST различать valid zero, empty result, `UNKNOWN` и
datasource/query failure по роли панели.

### 4.5.1 Current-status / current-cause panels

- `null` MUST рендериться как `UNKNOWN`.
- `or vector(0)` запрещён.
- Missing telemetry MUST оставаться fail-closed, а не превращаться в synthetic
  healthy state.
- First-screen current-status panels generally SHOULD NOT use Grafana-selected
  range as their primary semantics.
- Provider Health first screen uses current-status gauges only; range evidence is collapsed (epic #6572) when
  the operator explicitly needs the selected time window to recover the last
  observed provider state/cause inside that range instead of a fixed 15m
  snapshot.

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
- Record forensic CLI/API surfaces MUST объяснять это distinction в first-screen CTA и
  в detail-table descriptions.
- `Monitor Explorer Backend Health` MUST terminate as healthy, explicit error,
  or valid empty. Blank/loading and error-icon + `No data` contradictions are
  render failures.

### 4.5.5 Telemetry-gap / trust-marker policy

- Trust-marker panels обязательны только там, где без них оператор не может
  безопасно интерпретировать first-screen verdict.
- Они required для surfaces наподобие `Runtime` и `Control Plane`, где zero
  counters без telemetry health могут вводить в заблуждение.
- Они не являются blanket requirement для всех dashboards.
- Control Plane status gates replay safety, checkpoint age/presence, and
  required telemetry through `bioetl_control_plane_current_status_trusted`.
- Runtime status gates the scoped runtime verdict with
  `bioetl_runtime_trust_gap_status_10m` through
  `bioetl_runtime_current_status_trusted`. A trust gap renders `INCOMPLETE`, not
  WARN/OK inferred from selected-range zero counters.

### 4.5.6 Compact Overview selected-range evidence

- `Runtime Blockers Trend`, `DQ Status Trend`, `Gold Lifecycle Trend`,
  `Historical Failures`, and `Recent Non-success Terminal Runs` on `bioetl-overview-v2`
  are retained as compact below-fold evidence panels.
- They MUST stay below the current L0 verdict path and MUST NOT be referenced as
  current `Status` / `Next Action` inputs.
- Descriptions MUST state role, selected scope, no-data semantics, and owner
  drilldown target.
- Missing samples, gaps, zero matching failures, or no terminal rows are
  selected-range evidence states, not proof of current `OK`.

## 5) Единый unit/decimals для схожих KPI (обязательно)

- Для счётчиков событий (`... Missing`, `... Incompatibilities`, `... Failures`) использовать `unit=short`, `decimals=0`.
- Для timestamp KPI (`Latest Successful Data Timestamp` и аналогичные) использовать `unit=time:YYYY-MM-DD HH:mm`, `decimals=0`.
- Для долей/процентов (`... Rate`, `... Ratio`) использовать единый unit внутри dashboard-семейства (`percentunit` или `percent`) и согласованный `decimals` (обычно `0` или `2`).
- Схожий KPI в разных dashboards MUST иметь одинаковую пару `unit/decimals`.

## 6) QA Gate

### 6.0 Content contract и deterministic state fixtures

Каждая shipped Grafana-панель с integer `id`, включая row groups, navigation
shell и nested diagnostic panels, MUST иметь запись в
`contracts/panel-content-contract.yaml`. Запись задаёт семантическую роль,
tier, evidence scope, разрешённые terminal states, обязательные copy-элементы,
набор fixture cases и требуемые render profiles. Для shell/row panels допустим
`not_applicable`; это явное отсутствие собственного runtime verdict, а не
пропуск contract coverage. Contract не заменяет shipped Grafana JSON, а
обеспечивает его статическую, fail-closed трассировку.

Детерминированные state fixtures находятся в
`tests/fixtures/grafana/dashboard_states/`. Они различают `VALID_EMPTY`,
`TELEMETRY_ABSENT` и `ERROR`; пустой результат не может быть интерпретирован
как здоровое состояние. Проверки запускаются так:

```bash
uv run python -m scripts.engineering.qa.generate_dashboard_content_contract --check
uv run python -m scripts.engineering.qa.validate_dashboard_content_contract
uv run python -m pytest tests/integration/test_dashboard_content_contract.py \
  tests/integration/test_dashboard_state_fixture_contract.py -q
```

Optional render evidence может быть связано с registry fixture states без
подмены live datasource через
`rerender_grafana_screenshots.py --fixture-manifest tests/fixtures/grafana/dashboard_states/INDEX.json`.
В `render-manifest.json` сохраняются путь, SHA-256 и список заявленных cases;
по умолчанию live render path и его datasource semantics не меняются.

Базовая автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates
```

Проверка валидирует:

- color mode = `thresholds`
- стандартизованные threshold steps
- обязательный `UNKNOWN` mapping для `null`
- отсутствие top-level `gridPos` overlaps в
  `tests/integration/test_grafana_dashboard_first_screen_contract.py`
- `background` colorMode + explicit `OK/WARN/CRIT` value mappings для
  designated current-status severity stat panels

## 6.1) PromQL duplication policy (обязательно)

Штатный audit surface для duplicate-query обзора:

```bash
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates
```

Норматив:

- Exact duplicate PromQL across more than one panel MUST быть либо:
  - intentionally reused and audited with role-specific justification,
  - либо consolidated into a recording rule or a single canonical panel surface.
- Near-duplicate query families SHOULD оставаться panel-local only when они
  выражают одну и ту же metric family как sibling breakdown:
  - percentile triplets (`p50/p95/p99`) inside one latency panel,
  - stage-specific or status-specific variants inside one comparison surface.
- The automated near-duplicate budget is scoped to BioETL metric families
  (`bioetl_*`). Standard platform metrics such as Prometheus `ALERTS` remain
  reviewable as dashboard PromQL, but they do not spend the BioETL
  near-duplicate budget.
- Если один и тот же query family повторяется across multiple panels or across
  dashboards, приоритет такой:
  1. recording rule / shared canonical metric,
  2. explicit justification in dashboard audit/tests,
  3. raw duplication only as a temporary exception.

Current audited exact-duplicate reuse:

- `bioetl_dq_current_status` is intentionally reused by the compact `Status`
  card and the expanded `Monitor DQ Current Status` diagnostic in
  `bioetl-dq-v2`.
- `bioetl_runtime_current_status_trusted` is intentionally reused by the
  compact `Status` card and the expanded `Runtime Status` diagnostic in
  `bioetl-runtime`.
- The DQ weighted stat and trend are no longer an exact duplicate and have
  distinct time semantics: `Monitor: Data Quality Score (Volume-weighted)`
  uses a fixed seven-day (`[7d]`) latest-retained snapshot, while
  `Track: Data Quality Score Trend (Volume-weighted)` uses raw selected-range
  samples. Missing retained samples remain `UNKNOWN`, never a synthetic zero.
- `Monitor: Lineage Refs Missing` now has a single canonical owner:
  `bioetl-control-plane-v1`.
- `bioetl-dq-v2` MUST hand off to Control Plane with an explicit note/link
  instead of mirroring the same counter a second time.

Implementation guardrails:

- Justified exact duplicates MUST remain audited in the query-duplicate
  allowlist and integration query-governance tests.
- The report command is report-only; it is for discovery and review, not for
  automatic JSON rewrites.

## 7) UI-лексика навигации (обязательно)

Источник фиксированного словаря для `links[].title`: `docs/03-guides/dashboards/navigation-contract.md`.

Правила:
- Названия top-level ссылок MUST совпадать с каноническими строками из navigation contract: `Run Explorer`, `Replay Readiness`, `Run Overview`, `6. Incident Workspace` (visible bus; Data Quality is contextual; **no** `Silver Reject Explorer` / `Explore Logs` / `Explore Traces`).
- Формулировки вида `Back to Overview`, `5. Control Plane`, `6. Workflow Overview`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)`, `Next Recommended Drilldown`, and reintroduced adjunct titles, считаются legacy-лексикой и не допускаются в shipped top navigation.

Navigation panel 1000 renders the same four-chip composition on Replay Readiness,
Run Overview, Data Quality and Incident Workspace. Run Explorer uses row actions. It MUST use theme-safe contrast, a visible
focus state, and wrapping responsive layout at `1024px`.

### 7.1) Link title style-guide: Back / Open / Investigate

Используй единый шаблон для операторских ссылок:

- `Back to <Dashboard>` — только для возврата на предыдущий L0 уровень.
- `Open <Target>` — переход в соседний dashboard или внешний runbook без forensic-контекста.
- `Investigate <Target>` — переход в forensic/deep-dive surface (например, reject explorer, incident drilldown).

Норматив:
- Для top-level `links[]` в `grafana/dashboards/*.json` MUST использоваться только эти глаголы для action-link лексики (`Back`, `Open`, `Investigate`), кроме канонических имен dashboard (`2. Runtime`, `4. Provider Health`, и т.д.).
- Для `options.dataLinks` в критичных панелях предпочтителен `Open ...`; `Investigate ...` допустим для incident/deep-dive панелей.

### 7.2) Scope reset suffix в tooltip (обязательно)

Если link меняет scope (например, принудительно ставит `var-pipeline=unknown`, сбрасывает provider/adapter или stage, либо сбрасывает `var-run_type` на `All`), tooltip MUST содержать явный suffix:

- `Scope reset: ...`

Рекомендуемый шаблон:

- `Cross-scope handoff ... Scope reset: pipeline=unknown, run_type=All; provider/adapter not transferred.`

Если scope не меняется, используй нейтральный tooltip:

- `Preserves selected scope and time range.`

### 7.3) Role-based runbook CTA policy (обязательно)

Покрытие runbook CTA управляется ролью dashboard-а.

- `bioetl-overview-v2` является dashboard-routing-first surface: saved assessment
  routes to Replay Readiness, Data Quality and local Provider Evidence.
- `bioetl-incident-v1` owns selected-range workflow evidence and CURRENT triage.
  Range workflow counters do not need individual runbook links; retained fleet
  triage has four explicit local destinations.
- Replay Readiness routes its verdict to exact replay checks; validation may use
  the appropriate runbook. DQ routes to Run Explorer and saved evidence.
- Provider Evidence is saved preflight history; live provider incident runbooks
  belong on Incident. Run Explorer uses row passports, Report and exact-run links.
- Runbook URLs MUST follow the canonical GitHub blob pattern:
  `https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/<name>.md`.
- Dynamic alert runbooks are restricted to tracked literal runbook stems in the
  canonical query. Links preserve exact identity where applicable and time range.

## 7.1) L1 layout rule: answer-first above fold (обязательно)

Для L1 control-plane dashboards первый экран (above fold) MUST отвечать на
вопрос оператора без прокрутки:

- ровно один верхний triage-row с **3–5 KPI**;
- в этом же ряду MUST быть **ровно одна** явная панель next-step/drilldown;
- панели глубокой диагностики MUST быть вынесены в secondary rows, collapsed
  by default, с
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

## 8.1) Metadata policy: refresh, schemaVersion, iteration, tags

Metadata MUST follow repo policy rather than mechanical suite-wide rewrites:

- `refresh` and default `time.from` are governed by the machine-readable contract
  in `docs/03-guides/dashboards/contracts/navigation-links.yaml`.
  Operator-facing dashboards keep the L0/L1 baseline `time.from=now-12h` and
  `refresh=60s`; `bioetl-silver-reject-explorer` is the explicit forensic
  exception with `time.from=now-24h` and `refresh=1m`.
- `schemaVersion` MUST be `42` for canonical dashboards targeting the pinned
  Grafana `12.2.5` runtime. The FK selected-snapshot browser acceptance exposed
  Grafana's migration of legacy datasource names and query targets: the browser
  loads the migrated DTO even when the legacy API still returns schema `30`.
  The canonical generator therefore emits explicit provisioned datasource UID
  references and query-target inheritance before declaring schema `42`.
  Preserve queries, URLs and layout; never remove semantic differences from
  source/browser parity checks to make a capture pass. Static text panels must
  not acquire a fabricated default Prometheus query during migration.
- `iteration` is optional. If present, it MUST be a positive integer and should
  be used only for deliberate exported revision tracking, not added everywhere
  as decoration.
- `tags` MUST include the baseline suite tag `bioetl`. Additional role/domain
  tags MAY vary by dashboard (`overview`, `runtime`, `control-plane`,
  `provider`, `workflow`, `explorer`, etc.) when they improve search and
  discoverability.

## 8.2) Technical configuration policy: governed fields vs export noise

Shipped dashboards MUST distinguish between meaningful root configuration
invariants and benign Grafana export artifacts.

Governed root fields:

- `style` MUST be `"dark"` for every shipped dashboard.
- `editable` MUST remain `true`.
- `graphTooltip` MUST remain `1`.
- `hideControls` is optional; if exported explicitly, it MUST be `false`.

Benign export noise:

- Mixed panel-level `pluginVersion` values are NOT a standalone correctness failure.
- The repo MUST NOT bulk-rewrite shipped dashboard JSON just to force one
  `pluginVersion` across every panel unless a real Grafana import/export,
  rendering, or compatibility regression is proven first.
- When such a regression is proven, the migration plan SHOULD be documented and
  tested before any mechanical export rewrite lands.


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

## 9) DUX5 typography & copy residual

DUX5 artifacts remain historical audit evidence. Active authored-copy floors
are `body >= 12pt (16px)` and `panel heading >= 14pt (18.6667px)`; pinned
Grafana-managed chrome retains its theme baselines (`12px` body, `14px` native
panel title) and MUST pass 200% reflow without global CSS overrides. See
[`DASHBOARD_REQUIREMENTS.md`](../../01-requirements/DASHBOARD_REQUIREMENTS.md).
The screenshot protocol remains available at
[dux5-screenshot-regression-protocol.md](archive/audit-protocols/dux5-screenshot-regression-protocol.md),
and the historical copy dictionary remains at
[dux5-copy-dictionary.md](archive/audit-protocols/dux5-copy-dictionary.md),
but its former smaller floors are superseded.

### 9.1 Inline copy roles in authored HTML

Operator-facing HTML in text panels MUST distinguish five inline roles so
dashboard names, panel titles, and status tokens do not share one bold style.
Color MUST NOT be the only carrier of the role. Navigation-bus chips stay on
the existing theme-safe chip contract (`gap:8px`, chip `padding:0 8px`) and are
not this inline rule.

| Role | Visible form | HTML | Example |
| --- | --- | --- | --- |
| Dashboard | numbered title, bold | `<b>1. Trust</b>` | `1. Trust`, `Run Explorer` |
| Panel | Title Case, italic, not bold | `<em>Review Selected-Run Trust</em>` | first-screen and rail references |
| Status / scope | CAPS, not bold | plain `INCOMPLETE` | `OK`, `WARN`, `CRIT`, `UNKNOWN`, `INCOMPLETE`, `CURRENT`, `SELECTED RUN`, `TIME RANGE` |
| Field / API token | monospace, `16px` | `<code style="font-size:16px">trust_status</code>` | `run_id`, `processing_status` |
| Body | regular `16px` | no wrapper | sentences and actions |

Exceptions: the 18px operator-question line on `Inspect Scope & Evidence` keeps
`font-weight:700` as a heading, not as an inline role. Native Grafana panel
titles stay on the pinned theme token. Do not wrap panel titles in `<code>` or
status tokens in `<b>` / `<strong>`.

Pilot surface: `bioetl-control-plane-v1` authored text panels. Other shipped
dashboards keep their current markup until the same pass lands there.
Enforcement: `tests/integration/test_dashboard_operator_readability.py`.

### Saved assessment and accounting integrity

The Selected Run API preserves the frozen assessment and revision. Its Trust
table also checks the saved report's reconciliation: an explicit `FAILING`
balance displays `ERROR` with the saved verdict and delta in the explanation.
`saved_trust_status` retains the historical verdict; `accounting_integrity`
identifies this display guard. `NO REPORTED CONFLICT` does not prove complete
accounting when reconciliation is absent. Neither the saved report nor the
ledger is rewritten by this read-only check.
