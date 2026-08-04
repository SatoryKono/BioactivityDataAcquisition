______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-13'

______________________________________________________________________

# Dashboard Extension Guide (LLM)

> **Removed 2026-07-23:** Silver Reject Explorer dashboard, Loki/Tempo Explore adjuncts, Quarantine Explorer datasource (replaced by BioETL Ops HTTP on :8000).
> Use CLI ioetl quarantine inspect for record-level forensics. See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).



Дата сверки: **2026-07-13**
Источник истины: `grafana/dashboards/*.json`

Короткий playbook для LLM/AI-агента, который меняет или расширяет shipped
Grafana dashboards в BioETL.

## 1. Обязательная стартовая точка

Перед правкой dashboard:

1. Прочитай целевой JSON в `grafana/dashboards/`.
1. Сверь текущую navigation model и operator role dashboard.
1. Не выводи структуру dashboard по памяти, скриншотам или старым docs.
1. **Dashboard 2.0 first-screen checklist** ([operator-ux-v2.md](operator-ux-v2.md)):
   evidence before prose; ≤4 CTAs; empty-state taxonomy; preserve
   `${__url_time_range}`; no `run_id` in PromQL; verdict ontology
   ([verdict-ontology.md](verdict-ontology.md)).

## 2. Текущая модель shipped dashboards

- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO` — единая top-level
  шина.
- На каждой из восьми shipped страниц navigation panel `id=1000` визуально
  показывает полный bus `0..6`; текущий dashboard рендерится как disabled
  theme-safe item, а machine-readable `panel.links` сохраняют omit-self
  contract. Навигация MUST оставаться читаемой в dark/light themes и
  переноситься без обрезки на viewport `1024px`.
- Каноническая surface этой шины — navigation panel `id=1000`. Root
  `dashboard.links[]` MAY be empty, если те же handoff already shipped через
  panel `id=1000` и header row рядом с Grafana variables не должен дублировать
  bus links.
- Любые дубли dashboard-to-dashboard links из одного dashboard в один target
  dashboard запрещены, если только machine-readable contract в
  `contracts/navigation-links.yaml` явно не требует repeated panel-level CTAs
  для critical surfaces.
- Во всех shipped navigation panels `id=1000` bus `0..6` only.
  Do **not** reintroduce `Silver Reject Explorer`, `Explore Logs`, or
  `Explore Traces` (removed 2026-07-23). Current dashboard item MUST stay
  visible and disabled instead of disappearing from the visual bus.
- Navigation panel links MUST open in the same window; do not ship
  `target="_blank"` in panel `id=1000` HTML.
- Layout hierarchy follows the dashboard design system:
  `Tier 1` answer surface first, `Tier 2` current context second,
  `Tier 3` selected-range evidence below fold, `Tier 4` diagnostic/detail rows
  below fold. Tier 4 row groups ship collapsed by default; full render/audit
  paths MAY expand them explicitly when secondary or noisy detail must be
  reviewed.
- Primary dashboards `0..5` expose the shared operator context shell:
  `$workflow`, `$pipeline`, `$run_type`, `$run_id`, plus role-specific
  extensions. `run_id` remains HTTP-backed identity context for the `ID` panel,
  is preserved between primary dashboards, and MUST NOT leak into Prometheus
  queries or Silver forensic selectors.
- `1. Overview` intentionally ships with `Workflow=All`, `Pipeline=All`,
  `Run Type=All`, and `Run ID=-` as its default entry scope.
- Во всех остальных pipeline/provider dashboards `$pipeline` и `$provider`
  остаются single-select where they are primary selectors; explicit fallback
  для неизвестного контекста — `unknown`.
- `$run_type` всегда использует include-all fallback; cross-dashboard links MUST
  default missing run-type context to `All`, not `unknown`.
- Переходы в `3. Provider Health` из pipeline-scoped dashboards сохраняют
  hidden `pipeline_context=$pipeline` для обратного перехода и fail-close'ятся
  к `provider=unknown`, если source dashboard не может доказать валидный
  provider value для target contract.
- Shared `Inspect Scope & Evidence` / `Status` / `ID` / `Processed Records` panels use ids
  `9400..9403` on primary dashboards outside Overview. `Status` is
  role-specific; `Processed Records` is current compact Bronze/Silver/Gold
  stage/outcome accounting evidence from `/ops/observability/processed-records`.
  When `$run_id` is selected, the HTTP endpoint resolves exact-run rows from
  RunLedger artifact/metrics evidence; otherwise it falls back to
  `bioetl_processed_records_*` recording rules with `value` and formatted
  canonical `percentage` columns. It includes zero-valued outcome rows, hides
  internal `row_status`, and intentionally omits status, accounted subtotal,
  and delta rows; it never introduces `run_id` Prometheus labels and never
  replaces the dashboard-specific `Status` / `First Action` decision path.

Если правка меняет эту модель, синхронизируй docs в том же change set.

## 3. Обязательные invariants

- Не меняй `uid` без явной migration reason.
- Не invent metric names — используй только реально существующие метрики.
- Не добавляй high-cardinality filters/labels в summary-panels без необходимости.
- Для нового operator dashboard или first-screen redesign сохраняй contract:
  `ONE BIG QUESTION`, current scope, provenance summary и `First action`.
- Silver Reject Explorer removed; forensic IDs stay on CLI quarantine inspect only
  context shell. It stays bounded to forensic `pipeline/run_type` plus
  `reason_code`, `field`, `quarantine_run_id`, and `payload_hash` selectors.
  Generic links into the explorer MUST NOT map primary `$run_id` into
  `$quarantine_run_id`; explicit record/payload drilldowns may use forensic
  selectors only when the source surface owns that evidence.
- Для cross-dashboard links не полагайся на blanket `includeVars=true`:
  передавай только target-scoped `var-*` параметры. Для primary dashboards это
  общий `workflow/pipeline/run_type` shell плюс preserved `run_id`; для Silver
  Explorer это bounded `pipeline/run_type`.
- Visual HTML anchors in navigation panel `id=1000` and machine-readable
  `panel.links` MUST preserve the same target-scoped variables. Operator clicks
  on the visible bus are the primary handoff path, so do not update only
  `panel.links` while leaving stale `options.content` URLs.
- Не копируй forensic identifiers (`quarantine_run_id`, `payload_hash`) в
  Prometheus dashboards, summary panels или generic drilldowns. Shared `run_id`
  is allowed only as HTTP-backed identity context between primary dashboards.
- Не используй encoded Loki interpolation по `$pipeline/$provider` как источник истины.
- Не превращай `Alert Conditions` в “real alert engine”, если datasource/state этого не поддерживает.
- Не добавляй datasource health tiles по умолчанию. Сначала докажи, что без
  trust marker оператор не сможет отличить empty scope, telemetry gap и backend
  failure.

## 4. Query conventions

### Prometheus

Если отсутствие серии означает “событий нет”, а не “источник сломан”, используй:

```promql
sum(increase(metric_name[24h])) or vector(0)
```

Если отсутствие серии должно остаться диагностическим сигналом, не маскируй его
через `or vector(0)`.

Для histogram/rate latency panels это правило особенно строгое: `No data`
обычно означает “нет samples / нет probe activity / scrape gap”, а не
`0s latency`. `or vector(0)` допустим для count-like healthy-zero panels, но не
для p95 latency unless issue body explicitly justifies zero-as-valid semantics.

### Loki / Tempo

**Do not ship** Loki LogQL panels, Tempo TraceQL panels, or Explore Logs/Traces
navigation links. Those stacks were removed from the BioETL monitoring surface
on 2026-07-23. Prefer Prometheus metrics and structured log files under
`reports/logs/` / operator CLI.

## 5. Docs cascade rule

Если изменилось хотя бы одно из следующего:

- title dashboard
- navigation links
- time range / refresh
- operator role dashboard
- drilldown behavior
- first-screen scope / provenance / first-action semantics

Проверь также:

- Loki/Tempo drilldown links must **not** be reintroduced.
- HTTP identity panels use datasource **BioETL Ops HTTP** (`bioetl:8000`), not
  Quarantine Explorer. Note for legacy text that still mentions Grafana TraceQL
  handoffs: those handoffs are retired; do not bind `${run_type:regex}` for
  `includeAll` variables. Grafana
  может схлопнуть `All` в пустой regex `()`.
- Runtime condition-summary panels не теряют direct runbook links.

то обнови минимум:

- `docs/03-guides/dashboards/README.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/05-operations/01-monitoring-guide.md`
- `grafana/README.md`

## 6. Verification protocol

Минимум:

```bash
uv run python -m json.tool grafana/dashboards/<dashboard>.json
uv run python -m pytest -q tests/integration/test_grafana_config.py
```

Если меняется observability navigation, дополнительно проверь реальный Grafana UI.

## 7. Definition of Done

- JSON валиден.
- Dashboard obeys current shipped navigation model.
- `No data` vs `0` выбрано сознательно, а не случайно.
- First-screen preamble сохраняет один operator question и не теряет scope /
  provenance / first-action semantics.
- Contract tests проходят.
- Docs синхронизированы в том же PR/change set.

## 8. Visual consistency gates

Перед merge каждый изменённый dashboard MUST пройти чеклист:

- [ ] Для всех `stat`/`gauge` панелей используется единый `color.mode=thresholds`.
- [ ] Для enum/status-панелей `stat`/`gauge` используется canonical `thresholds.steps`: green/null, orange/1, red/2; domain/policy gauges MAY use real-unit thresholds (`seconds`, ratios, tokens) when they match operator semantics.
- [ ] Для всех status-панелей задано единое no-data поведение: `null -> UNKNOWN (gray)`.
- [ ] Для first-screen current-status severity `stat` panels используется `options.colorMode=background`; range evidence и raw-state diagnostic panels не форсируются в этот стиль автоматически.
- [ ] Для first-screen current-status severity `stat` panels заданы explicit value mappings `0=OK`, `1=WARN`, `2=CRIT`, `null=UNKNOWN`.
- [ ] Для `gauge` panels используется `options.showThresholdMarkers=true` и `options.showThresholdLabels=false`, если panel-specific rationale не документирует другое поведение.
- [ ] Для `table` panels используются только утверждённые `custom.cellOptions.type`: `auto`, `color-background`, `color-text`; status/route field overrides используют `color-background`.
- [ ] Для comparative/multi-series `timeseries` используется `options.tooltip.mode=multi` и `options.tooltip.sort=desc`.
- [ ] Для scalar trend `timeseries` используется `options.tooltip.mode=single` и sorting остаётся `none`/omitted.
- [ ] Для терминов статусов применяется единая таблица mapping из `docs/03-guides/dashboards/design-system.md` (раздел **1.1 Canonical mapping: L0 vs diagnostic dashboards**).
- [ ] В L0 dashboards используется только `OK/WARN/CRIT/UNKNOWN`; alias-термины (`DEGRADED/BROKEN/HEALTHY`) допустимы только в диагностических deep-dive поверхностях и с явным alias mapping в description.
- [ ] Для Prometheus current-status/current-cause panels отсутствует invalid zero-fallback (`or vector(0)`); zero fallback допустим только для true event counters.
- [ ] Для HTTP-backed forensic panels (`BioETL Ops HTTP`) descriptions/noValue copy различают zero matching rows, invalid scope/filter chain и backend failure.
- [ ] Заголовки и описания новых панелей соответствуют шаблонам из design system.
- [ ] Пройдена автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
```


## 9. Panel naming and description policy

For every new or modified panel title, use an action-first pattern:

- `Monitor ...` for current state / health snapshots
- `Inspect ...` for diagnostic drilldown detail
- `Track ...` for trend, rate, or historical evolution

Description for new/modified status panels MUST include the canonical mapping:

- `0` = healthy/ok
- `1` = warning/degraded
- `>=2` = critical/failing
- `null` = no data / unknown

Good naming examples:

- `Monitor Current Provider Health Status`
- `Track Provider Failure Rate`
- `Inspect Top Reject Reasons`

Bad naming examples:

- `Provider Health`
- `Top Reject Reasons`
- `Status`
