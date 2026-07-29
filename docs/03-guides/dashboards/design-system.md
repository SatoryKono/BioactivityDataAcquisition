# Dashboard Design System (BioETL)

Дата актуализации: **2026-07-28**
Источник истины: `grafana/dashboards/*.json`

**Dashboard System 2.0:** operator first-screen contract and verdict model live in
[operator-ux-v2.md](operator-ux-v2.md) and [verdict-ontology.md](verdict-ontology.md).
Prose-first first screens (giant Provenance / multi-paragraph First Action without
evidence) are **deprecated**. Evidence strip + status + ≤4 CTAs is required.

## 1) Единая семантика состояний (обязательно)

Для status-панелей (`stat`/`gauge`) применяется фиксированная палитра:

- **OK** → `green`
- **WARN** → `orange`
- **CRIT** → `red`
- **UNKNOWN** → `gray`
- **INCOMPLETE** → `gray` (required evidence is missing or stale; never OK)
- **ERROR** → `red` for an explicit query/datasource/backend failure

`UNKNOWN` обязателен как явное отображение no-data/null через mapping:
- `null` → текст `UNKNOWN` + цвет `gray`.

Terminal-state vocabulary is role-aware:

- `VALID EMPTY` / `valid-empty` — query completed and the selected scope has
  zero matching rows/events; neutral gray, with the next action in panel copy.
- `TELEMETRY ABSENT` — required metric family is absent; neutral gray and a
  scrape/target action. On headline trust gates this resolves to `INCOMPLETE`.
- `N/A` — the signal is not applicable to the selected lifecycle/scope; neutral
  gray and never a healthy verdict.
- `LOADING` — transient only. It MUST NOT remain in accepted render evidence.
- A blank panel body is not a state and MUST fail reproducible capture.

### 1.1 Canonical mapping: L0 vs diagnostic dashboards

| Dashboard surface | Numeric range | Canonical status term | Visualization color |
| --- | --- | --- | --- |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `0` | `OK` | `green` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `1` | `WARN` | `orange` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `>=2` | `CRIT` | `red` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `null` | `UNKNOWN` | `gray` |
| **Evidence-aware trust gates** (`0. Control Plane`, `2. Runtime`) | `3` | `INCOMPLETE` | `gray` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `<1` | `OK` *(alias `HEALTHY` optional)* | `green` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=1 and <2` | `WARN` *(alias `DEGRADED` optional)* | `orange` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=2` | `CRIT` *(alias `BROKEN` optional)* | `red` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `null` / no data | `UNKNOWN` | `gray` |

Норматив:
- В **L0 operator dashboards** MUST использоваться только термины `OK/WARN/CRIT/UNKNOWN`.
- `0. Control Plane` and `2. Runtime` MAY additionally use `INCOMPLETE` when
  required checkpoint/scrape/rule evidence is missing or stale. Numeric `3`
  remains `UNKNOWN` on Overview/DQ surfaces that do not define this trust gate.
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
| Current-status `stat` | `fieldConfig.defaults.color.mode=thresholds`; `options.colorMode=background` for designated first-screen severity cards; `null -> UNKNOWN` mapping where the panel is fail-closed. |
| Selected-range trend `stat` | `options.colorMode=value`; `options.graphMode=area`; threshold colors must match the measured operator risk. |
| Selected-range count `stat` | `options.colorMode=value`; `options.graphMode=none`; `or vector(0)` only when missing series means zero events. |
| Percentage, score, latency, or duration `gauge` | `options.showThresholdMarkers=true`; `options.showThresholdLabels=false` unless a panel-specific exception is documented with operator rationale. |
| Status or route `table` column | Use `custom.cellOptions.type=color-background` **only via field override** for the status/Value field. |
| Data or forensic `table` | Use `custom.cellOptions.type=auto` as the table default when an explicit default is configured; datasource/plugin defaults are allowed for HTTP-backed forensic tables. |

**Forbidden:** table-wide default `color-background` without field overrides (paints Time/name/pipeline as severity).
| Comparative or multi-series `timeseries` | `options.tooltip.mode=multi`; `options.tooltip.sort=desc`. |
| Scalar trend `timeseries` | `options.tooltip.mode=single`; `options.tooltip.sort=none` or omitted. |

Allowed table `custom.cellOptions.type` values are `auto`, `color-background`,
and `color-text`. Introducing a new table cell option type requires updating
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

Shared headline precedence is fail-closed:
`ERROR > INCOMPLETE/UNKNOWN > CRIT > WARN > OK`. `ERROR` owns an explicit
query/datasource/backend failure; `INCOMPLETE` or `UNKNOWN` owns the verdict
when required evidence cannot support a truthful business-severity decision.
Only complete evidence may resolve to `CRIT`, `WARN`, or `OK`. Presentation
colors never override this ordering.

## 4.1) First-screen responsibility and panel decision matrix (обязательно)

Каждый shipped dashboard имеет ровно один основной операторский вопрос. Первый
экран должен отвечать на этот вопрос через current-status сигналы, а не через
выбранный Grafana range. Range evidence, raw counters и forensic details
помещаются ниже первого экрана или в dedicated drilldown.

| Dashboard | First-screen responsibility | Current-status rules | Selected-range evidence | Drilldown / forensic surface |
| --- | --- | --- | --- | --- |
| `bioetl-overview-v2` | Что сейчас broken/degraded и куда идти дальше? | `bioetl_l0_status`, `bioetl_l0_next_action_route`, `bioetl_l0_input_status` | collapsed `L1 Historical Trends` and `Range Evidence` rows | linked L1 dashboards |
| `bioetl-runtime` | Что прямо сейчас блокирует runtime execution? | `bioetl_runtime_current_status_trusted`, `bioetl_runtime_current_blocker_reason`, `bioetl_runtime_trust_gap_status_10m` | failed/no-record runs, stage lag/backlog trends, shutdown intervals | collapsed Detect/Localize/Escalate rows, Loki/Tempo handoff |
| `bioetl-provider-health-v2` | Какой provider сейчас degraded/failing и почему? | `bioetl_provider_current_status`, `bioetl_provider_current_cause` | health-check counters, failure/degraded trends, latency/rate-limit history | provider detail panels and runbook links |
| `bioetl-dq-v2` | Каково текущее DQ состояние и первое действие? | `bioetl_dq_current_status`, `bioetl_dq_current_reason` | explicitly labelled CURRENT / SELECTED RUN / TIME RANGE evidence; freshness hours with SLA 24/72 | `bioetl-silver-reject-explorer`, collapsed DQ diagnostics |
| `bioetl-control-plane-v1` | Можно ли доверять control plane и безопасно replay/resume? | `bioetl_control_plane_current_status_trusted`, replay/checkpoint/manifest/telemetry evidence | manifest/ledger/checkpoint/audit histories | collapsed replay-safety diagnostics and runbooks |

Decision matrix:

| Panel class | Belongs on first screen? | Query contract | Naming contract |
| --- | --- | --- | --- |
| Current status / current reason | Yes | Fixed current windows or recording rules; MUST NOT use `$__range` | `Monitor ...` or `Inspect ...` |
| Next action / route | Yes | Low-cardinality route/action rules; preserve `UNKNOWN` when data is missing | `Next Action`, `First Action`, or `Inspect ...` |
| Selected-range count/rate/trend | No; compact evidence may appear below first-screen answer bands | MUST use `$__range`, `$__interval`, or explicit range wording. L1 current recording rules may be trended over the selected dashboard window only when the description says selected-range evidence and not current verdict. | `Track ... in Range` or description says selected range |
| Raw counter / histogram / latency evidence | No | Preserve no-data unless zero is semantically valid | `Track ...` |
| Forensic row/table/details | No | May carry scoped IDs only in dedicated explorer surfaces | `Inspect ...` or `Investigate ...` |

Normative rules:
- Primary dashboards `0..5` SHOULD expose the shared operator context shell
  before dashboard-specific evidence rows: `Provenance`, `Status`, `ID`, and
  `Processed Records`. These panels standardize context, identity, and
  selected-range throughput evidence, but they do not override the
  role-specific first-action/current-cause panels.
- First-screen current-status panels MUST NOT use `$__range`.
- Range panels MUST include selected-range wording in title or description.
- Compact Overview evidence panels below the first screen MAY reuse L1 current
  recording rules as selected-range trend evidence, but their descriptions MUST
  say they do not determine `L0 Status` or `Next Action`.
- Historical/range evidence MUST NOT be treated as a recovery verdict: zero
  matching rows or missing samples do not prove current `OK` unless the panel is
  explicitly a zero-valid event counter.
- Top-level `gridPos` rectangles in a shipped dashboard MUST NOT overlap;
  navigation, scope, first-action, current-status, range evidence, and expanded
  rows must occupy explicit non-overlapping grid bands.
- Top-level root layout MUST NOT leave unexplained empty row gaps between
  adjacent bands; if a dashboard intentionally adds vertical breathing room, the
  exception must be justified in the dashboard audit or docs mirror.
- `or vector(0)` is allowed only for event-count panels where missing series
  means zero events; status panels preserve `UNKNOWN`.
- Deep details (`run_id`, `payload_hash`, record-level tables) MUST NOT appear
  on first-screen status rows.
- DQ values MUST identify their evidence scope as `CURRENT`, `SELECTED RUN`, or
  `TIME RANGE` in a visible title/banner/value mapping. A selected-range value
  must not be read as exact-run evidence.
- DQ freshness uses hours end-to-end in the panel: query output, unit, title,
  and thresholds. The explicit SLA is WARN at `24h`, CRIT at `72h`.

### 4.1.1 Shared operator context shell

The shared shell is derived from `1. Overview` and applies to primary
dashboards `0. Control Plane`, `2. Runtime`, `3. Provider Health`,
`4. Data Quality`, and `5. Workflow`.

| Panel | Canonical ID | Role | Data contract |
| --- | ---:| --- | --- |
| `Provenance` | `9400` | Question banner | Visible text contains only the primary dashboard question; workflow, pipeline, run_type, run_id, and selected-time context stay in the panel tooltip/description. |
| `Status` | `9401` | Compact dashboard verdict | Prometheus status for the dashboard role; no `$run_id` Prometheus filtering. `5. Workflow` is selected-range evidence and must say so. |
| `ID` | `9402` | Local control-plane identity | HTTP/Infinity `Quarantine Explorer` table from `/ops/control-plane/identity-table`; exact `run_id` is preserved HTTP identity context across primary dashboards. The two visible columns are `parameter` and `value`; rows cover run/manifest IDs, Provider.Entity version, contract schema, execution flags, replay capability/mode, checkpoint anchors, optional composite run, and identity health. |
| `Processed Records` | `9403` | Current stage/outcome accounting evidence | HTTP/Infinity table from `/ops/observability/processed-records`, backed by compact `bioetl_processed_records_*` recording rules and canonical `bioetl_stage_records_total` outcomes. It shows non-zero Bronze, Silver outcome, and Gold outcome rows only, with `value` plus formatted `percintage` columns. `value` uses a space as the thousands separator, is left-padded to the displayed `bronze [total]` width, and is right-aligned in the table. Bronze is `100%`; `silver [valid]` and `gold [valid]` use one decimal; secondary outcomes use up to three decimals with trailing zeroes trimmed. Silver and Gold percentages use Bronze total. Visible Silver rows get a red row background when Silver accounted records sum below Bronze total; visible Gold rows get a red row background when Gold accounted records sum below `silver [valid]`. Status, accounted subtotal, and delta rows stay out of the compact table. Missing accounting series are no-data/instrumentation gaps, not OK. |

Normative rules:
- `run_id` MUST NOT be added to Prometheus label filters.
- Primary dashboard `run_id` option lists MUST be loaded through the local
  control-plane selector catalog (`/ops/control-plane/filter-options`) using
  the visible `workflow`, `pipeline`, and `run_type` shell context. Coherent
  selector tuple resolution belongs to `/ops/control-plane/selector-context`,
  not to Prometheus labels.
- `Processed Records` MUST show bounded Bronze/Silver/Gold stage/outcome
  accounting evidence. It intentionally omits reconciliation status, accounted
  subtotal, and delta rows, and MUST NOT replace the dashboard role-specific
  `Status` or `First Action` decision path.
- `Processed Records` percentage evidence MUST stay denominator-explicit:
  Bronze renders `100%`, and all Silver and Gold outcome rows divide by
  `bronze [total]`. Zero-valued rows are omitted from the compact table, but
  missing accounting series remain no-data, not zero. The visible `value` and
  `percintage` fields are display-token strings formatted by the local HTTP
  helper so Grafana can render row-consistent text color while showing compact
  values such as `10 000`, `   851`, `91.0%`, `90.1%`, `8.51%`, and `0.47%`.
- `Processed Records` row-background evidence MUST stay accounting-explicit:
  if `silver_valid_records + silver_quarantined_records + silver_skipped_records
  + silver_filtered_out_records + silver_deduplicated_records` is below
  `bronze_records`, visible Silver rows use a red row background. If
  `gold_written_records + gold_quarantined_records
  + gold_excluded_by_contract_records + gold_skipped_records
  + gold_deduplicated_records` is below `silver_valid_records`, visible Gold
  rows use a red row background. Non-deficit rows MUST map the empty
  `row_status` value to a transparent background, not to OK/green; missing
  accounting series do not count as zero.
- `Processed Records` current reconciliation MUST NOT use `$__range`,
  `or vector(0)`, or `run_id`/manifest/raw payload labels in Prometheus.
  Exact-run HTTP reads MAY pass `$run_id` to resolve rows from RunLedger source
  of truth; that selector must not become a Prometheus label.
- Provider Health keeps `$provider` as the primary current-status selector even
  though the shared shell also exposes `$pipeline` and `$run_type`.
- Workflow keeps `$status`, `$step_status`, and `$step_kind` as workflow-local
  evidence filters; `$pipeline`, `$run_type`, and `$run_id` are context/identity
  aids unless a future rule defines truthful intersection semantics.

## 4.2) Layout grammar by dashboard role (обязательно)

Shipped dashboards do not share identical geometry, but they MUST share the
same answer-first reading order.

| Dashboard role | Shipped dashboards | Above-the-fold responsibility | Lower bands |
| --- | --- | --- | --- |
| L0 answer-first hub | `bioetl-overview-v2` | current answer, next route, bounded mirrors | historical context, routing aids, collapsed-by-default diagnostics |
| L1/L2 triage | `bioetl-runtime`, `bioetl-control-plane-v1`, `bioetl-provider-health-v2`, `bioetl-dq-v2` | current verdict, first action, causes, trust markers | selected-range evidence, collapsed-by-default diagnostics |
| Selected-range operational evidence | `bioetl-workflow-overview` | selected-range operational verdict and immediate fallout | lower evidence bands, optional collapsed-by-default diagnostics |
| Forensic explorer | `bioetl-silver-reject-explorer` | scope semantics, no-data guidance, bounded summary | row-level browsing, record details, forensic tables |

Normative rules:
- Every shipped dashboard MUST answer its primary operator question before the
  first evidence-heavy row.
- Historical or selected-range evidence MUST NOT visually precede current-state
  answer surfaces on L0/L1/L2 dashboards.
- Forensic explorer surfaces are exempt from Prometheus-style symmetry, but
  they still MUST keep scope semantics and first action above row-level detail.

## 4.3) Visibility tiers and collapse policy (обязательно)

Every shipped dashboard should classify panels into one of four tiers.
Answer surfaces stay visible; forensic/detail rows are collapsed by default and
opened only after the summary identifies a relevant branch:

- `Tier 1`: always-visible answer surface
- `Tier 2`: always-visible supporting current context
- `Tier 3`: below-fold selected-range evidence
- `Tier 4`: collapsible diagnostics, raw evidence, tracing-only detail, rare
  forensic breakdowns

Normative rules:
- `Tier 1` MUST remain visible without extra clicks and MUST contain current
  status / verdict, first action, or current causes needed for first-pass
  triage.
- `Tier 2` MAY add KPI context, trust markers, or bounded mirrors, but MUST
  support `Tier 1` rather than compete with it.
- `Tier 3` belongs below the answer bands unless the dashboard role is itself
  selected-range evidence.
- `Tier 4` SHOULD live below fold and be collapsed by default when it is
  tracing-only, raw, verbose, or not required for first-pass operator triage.
- The only copy of a critical signal MUST NOT live exclusively inside a
  diagnostic row.
- Overview keeps the deviation-first `Inputs` matrix visible and moves the six
  repeated subsystem mirrors into collapsed `Diagnostics & Docs`.
  `Alert/SLO Triage` remains the intentional expanded decision-row exception
  immediately after the compact matrix so firing critical impact is visible;
  `Status` and `First Action` retain the first route above it. Runtime
  Detect/Localize/Escalate, Control Plane incident rows, Provider detail, DQ
  forensic rows, Workflow Step Diagnostics, and the Silver trend/record rows
  remain collapsed in the shipped layout.
- Audit tooling MAY expand collapsed rows to materialize and review their full
  content; that audit mode does not change the shipped progressive-disclosure
  default.

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
- `Silver Reject Explorer` MUST объяснять это distinction в first-screen CTA и
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
  `Historical Failures`, and `Recent Terminal Runs` on `bioetl-overview-v2`
  are retained as compact below-fold evidence panels.
- They MUST stay below the current L0 verdict path and MUST NOT be referenced as
  current `Status` / `Next Action` inputs.
- Descriptions MUST state role, selected scope, no-data semantics, and owner
  drilldown target.
- Missing samples, gaps, zero matching failures, or no terminal rows are
  selected-range evidence states, not proof of current `OK`.

## 5) Единый unit/decimals для схожих KPI (обязательно)

- Для счётчиков событий (`... Missing`, `... Incompatibilities`, `... Failures`) использовать `unit=short`, `decimals=0`.
- Для timestamp KPI (`Latest Successful Data Timestamp` и аналогичные) использовать `unit=dateTimeAsIso`, `decimals=0`.
- Для долей/процентов (`... Rate`, `... Ratio`) использовать единый unit внутри dashboard-семейства (`percentunit` или `percent`) и согласованный `decimals` (обычно `0` или `2`).
- Схожий KPI в разных dashboards MUST иметь одинаковую пару `unit/decimals`.

## 6) QA Gate

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
- Названия top-level ссылок MUST совпадать с каноническими строками из navigation contract (например: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`, `Silver Reject Explorer`).
- Explore-ссылки MUST использовать короткие названия: `Explore Logs` и `Explore Traces`.
- Формулировки вида `Back to Overview`, `5. Control Plane`, `6. Workflow Overview`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)`, `Next Recommended Drilldown` считаются legacy-лексикой и не допускаются в shipped top navigation.

Every navigation panel renders the same ordered composition on all eight
shipped dashboards: bus `0..6`, `Silver Reject Explorer`, `Explore Logs`,
`Explore Traces`. It MUST use theme-safe contrast, a visible focus state, and
wrapping responsive layout at `1024px`; no dashboard-specific omission is
allowed.

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

### 7.3) Role-based runbook CTA policy (обязательно)

Покрытие runbook CTA управляется ролью dashboard-а, а не blanket-правилом
“каждая current/error/blocker/failed/skipped panel обязана вести в runbook”.

Норматив:

- `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-provider-health-v2`,
  `bioetl-dq-v2` и `bioetl-silver-reject-explorer` считаются operator/forensic
  surfaces. Их критичные панели SHOULD иметь actionable CTA; этот CTA MAY вести
  в runbook, соседний dashboard, либо в оба target-а, если исключение явно
  оправдано.
- `bioetl-overview-v2` является dashboard-routing-first surface. Panel-level
  CTA здесь MAY оставаться dashboard-only и по умолчанию не требует прямых
  runbook links.
- `bioetl-workflow-overview` является selected-range evidence surface. Его
  четыре summary counters selected-range evidence не требуют panel-level
  runbook links; shipped `First Action` остаётся единственным
  оправданным dashboard-handoff CTA exception на этой странице.
- Если используется runbook link, URL MUST follow canonical GitHub blob pattern:
  `https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/<name>.md`
- Названия runbook links SHOULD оставаться domain-specific (`Open Runtime
  Troubleshooting Runbook`, `Open Provider Incident Runbook`, `Open Quarantine
  Management Runbook`), а не схлопываться до generic `Open Runbook`.
- Одна panel MUST NOT смешивать конфликтующие runbook families, если такое
  исключение не задокументировано и не прошло review.

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
- `schemaVersion` MAY remain `30` or `39` until an explicit Grafana migration
  decision is approved. Do not bulk-upgrade exported JSON mechanically just to
  force one number across the suite.
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

Operator reading-order, state classes, and typography floors are normative in [dux5-copy-dictionary.md](dux5-copy-dictionary.md). Screenshot regression protocol: [dux5-screenshot-regression-protocol.md](dux5-screenshot-regression-protocol.md).
