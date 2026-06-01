______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# Dashboards Docs Index

Дата сверки: **2026-05-13**
Источник истины: `grafana/dashboards/*.json`

## Актуальные документы

- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе, включая runtime adaptive-memory triage.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `v3.0/` — draft-spec ветка для следующей линии дашбордов: execution-aware template, selector-resolution mirror и `1. Overview` hybrid L0 plan.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `variable-reference.md` — человеческий contract для shipped dashboard variables: role, fallback, scope, propagation.
- `selector-architecture.md` — selector taxonomy, dashboard families, hidden handoff model и future execution-selector design.
- `dashboard-v2-updates.md` — active changelog по текущей shipped surface,
  selector/navigation contract и UX evidence links для последних JSON-изменений.

Текущий shipped Explore handoff:

- Loki использует безопасный baseline `{job="bioetl"}`.
- Tempo использует contextual TraceQL filters по текущему dashboard scope (`pipeline` или `provider`); runtime `run_type` не шиппится в TraceQL handoff из-за include-all selector semantics.
- `bioetl-runtime` остаётся Prometheus-first в tracing-off режиме: Loki log-hygiene panels теперь живут в collapsed row `Tracing-only Log Hygiene`, а базовый triage path не требует Loki/Tempo datasource.
- Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor
  `0` to `bioetl_runtime_pipeline_run_type_universe`, GLOBAL provider handoff
  anchors `0` to `bioetl_provider_current_status`, and missing scope remains
  `UNKNOWN`. Unstructured Loki hygiene renders parsed `.__error__`, not the
  template function form.

Текущий reproducible render contract:

- Full-surface dashboard audits must use the Playwright screenshot path from
  `python -m scripts.ops rerender-grafana`, because that path expands collapsed
  rows before full-page capture.
- `python -m scripts.ops check-grafana-audit-preflight` must report
  `expanded-row-capture: ok` before a full UX/render audit can claim collapsed
  diagnostic rows were reviewed.
- Grafana Render API screenshots remain acceptable for render/auth smoke
  evidence, but they are not sufficient for the collapsed-row audit
  acceptance criterion.
- On Linux, `setup_grafana_screenshot_runtime.sh` is the canonical bootstrap
  for repo-local Playwright plus the supported headless Chromium shared
  library surface.

Текущая навигационная модель:

- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow` образуют единую top-level шину.
- На каждой странице navigation panel `id=1000` визуально показывает полный bus `0..5`; текущий dashboard рендерится как disabled dark-gray item, а machine-readable `panel.links` сохраняют omit-self contract.
- Каноническая shipped surface этой шины — text navigation panel `id=1000`;
  root `dashboard.links[]` не обязаны дублировать те же handoff в header row
  рядом с Grafana variables.
- Любые дублирующие dashboard-to-dashboard ссылки из одного dashboard в один
  target dashboard запрещены: переход должен быть ровно один.
- Во всех shipped navigation panels `id=1000`, кроме
  `bioetl-control-plane-v1`, после bus `0..5` закреплены global adjunct links:
  `Silver Reject Explorer`, `Explore Logs`, `Explore Traces`.
- `bioetl-control-plane-v1` является намеренным исключением: top-level
  navigation удерживает первый экран в dashboard/runbook flow и не уводит
  оператора напрямую в `Explore Logs` / `Explore Traces`; logs/traces
  расследование начинается из связанных dashboard handoff или runbook-пути.
- `Explore Traces` остаётся optional adjunct surface и считается доступным
  только для traced runs; если runtime использовал `NoOpTracing`, пустой Tempo
  result считается корректным поведением.
- Shipped `Explore Traces` handoff opens the explicit search-first Tempo route,
  bounds the initial window to `now-150m..now`, pins `var-ds=tempo`, uses
  `var-groupBy=resource.service.name`, and keeps only stable pipeline/provider
  TraceQL scope so Tempo metrics queries stay under the local limit and
  `includeAll` run-type selectors cannot collapse into an invalid empty regex.
- Navigation panel links intentionally открываются в том же окне, а не в новой
  вкладке.
- Переходы pipeline-scoped dashboards -> `3. Provider Health` сохраняют
  `pipeline_context=$pipeline`, но fail-close'ятся к `provider=unknown`; если у
  source dashboard нет adapter context, `adapter` не передаётся, а target
  dashboard раскрывает собственный fallback `All adapters`.

Текущая selector model:

- machine-readable SSOT: `contracts/selector-contracts.yaml`
- human-readable mirrors: `variable-reference.md` и `selector-architecture.md`
- shipped dashboards используют unified selector taxonomy by dashboard family,
  а не один flat universal selector list
- cross-dashboard handoffs явно передают общий `workflow/pipeline/run_type`
  shell через `var-*`; primary `run_id` additionally preserves exact HTTP
  identity between dashboards that expose that selector.

## First-screen policy header

Для всех operator dashboards действует единая policy-шапка:

- `ONE BIG QUESTION`
- current scope
- provenance summary
- availability / risk notes
- `First action`

Для shipped dashboards эта политика должна быть видима на первом экране через
scope/provenance/first-action блоки, current-status row, panel descriptions и
monitoring guide.

`bioetl-overview-v2` is the canonical L0 answer-first surface and now uses the
frozen `1. Overview v3` layout as its baseline. It answers one question:
what is currently broken or degraded in BioETL, and where should the operator
drill down first? The first screen materializes provenance/scope, `Status`,
`First Action`, `ID`, and `Processed Records`, then keeps current subsystem
summaries (`Control Plane`, `Runtime`, `Data Quality`, `Provider`,
`Data Validation`) plus selected workflow context. Historical evidence remains
below the current answer rows, and diagnostics routing lives under the collapsed
`Diagnostics & Docs (Logs / Traces / Raw Metrics)` row. Actual firing/pending
alert state is exposed in the collapsed `Alert/SLO Triage` row via Prometheus
`ALERTS`; this is presentation-only triage and does not duplicate alert-rule
business logic in dashboard queries.

`bioetl-control-plane-v1` is the `0. Control Plane` surface. It
starts with answer-first trust cards for replay safety state, checkpoint
freshness gap, ledger/manifest consistency, and telemetry presence for the
selected pipeline scope. Replay/checkpoint panels route to
`checkpoint-debugging.md`, while manifest/ledger evidence panels route to
`run-manifest-inspection.md`. **Known Blind Spots** and terminal-event
evidence live below fold in collapsed incident rows, not in the first-screen
trust block.

Control Plane keeps the shared compact `ID` shell panel (`9402`) backed by
`/ops/control-plane/identity-table`. The shell panel is a two-column summary of
run/manifest identity, Provider.Entity version, contract schema, execution
flags, replay capability and mode, checkpoint anchors, optional composite run
identity, and identity health. The deeper collapsed
`Identity evidence and remaining replay-safety signals` row uses
`/ops/control-plane/identity-evidence` for P0/P1/P2 anchors, identity gaps,
replay parentage, composite identity, checkpoint anchor comparison, and
copy-friendly full values. The HTTP rows include typed `source_type`,
`source_quality`, `drilldown_type`, and `drilldown_target` fields so operators
can route from anchors to manifest, ledger, effective config, contract,
snapshot, checkpoint, lineage, and artifact evidence without PromQL joins. This
row is the dashboard-approved place for
high-cardinality identity values; do not move those values into Prometheus
labels.

Global lookup/read-path panels stay separated in a dedicated
**Global diagnostics (non-pipeline scoped)** block and MUST remain unfiltered by
`$pipeline` / `$run_type`.

`bioetl-runtime`, `bioetl-provider-health-v2`, and `bioetl-dq-v2` are now
answer-first L2 incident surfaces. Their first visible rows use canonical
current-status recording rules (`bioetl_runtime_current_status`,
`bioetl_provider_current_status`, `bioetl_dq_current_status`) plus reason/cause
tables before any selected-range evidence. Range counters, trends, raw tables,
Silver reject breakdowns, logs, and traces stay below the first-screen answer
row or in collapsed diagnostic rows. `bioetl-provider-health-v2` also exposes
`Monitor Provider Telemetry Freshness` on the first screen so missing
`bioetl_provider_current_status` samples are treated as telemetry gap, not
healthy provider state.

`bioetl-overview-v2` exposes visible `workflow`, `pipeline`, `run_type`, and
`run_id` selectors. Pipeline/run_type remain the canonical current-status
Prometheus scope; `workflow` is evidence context, and `run_id` is a
control-plane-backed identity selector preserved for HTTP `ID`/details panels.
`Silver Reject Explorer` uses `quarantine_run_id` for its forensic run selector
so it cannot collide with the Control Plane `run_id` shell.

## KPI ownership (canonical vs mirrors)

Правило: KPI имеет один canonical dashboard (источник ответа) и может иметь
secondary mirrors только как локальный контекст. Mirror-карточки не должны
добавлять dashboard-to-dashboard links, если такой target уже есть в top-level
шине.

| KPI | Canonical dashboard | Secondary mirrors |
| --- | --- | --- |
| Status | `1. Overview` | `2. Runtime`, `0. Control Plane`, `5. Workflow` |
| First Action | `1. Overview` | `2. Runtime`, `3. Provider Health` |
| Inputs | `1. Overview` | `2. Runtime`, `4. Data Quality`, `0. Control Plane` |
| Data Validation | `1. Overview` | `2. Runtime`, `0. Control Plane` |
| Provider | `1. Overview` | `3. Provider Health` |
| Workflow | `1. Overview` | `5. Workflow` |
| Replay Safety State | `0. Control Plane` | `1. Overview`, `2. Runtime` |
| Checkpoint Freshness Lag | `0. Control Plane` | `2. Runtime` |
| Ledger/Manifest Consistency | `0. Control Plane` | `2. Runtime` |
| Provider Health (aggregated) | `3. Provider Health` | `1. Overview`, `2. Runtime` |
| DQ Status (Silver Reject / quality posture) | `4. Data Quality` | `1. Overview`, `2. Runtime` |

### Mirror policy for KPI cards

- Secondary dashboard cards, которые дублируют canonical KPI без нового
  измерения (другая гранулярность, иной период, дополнительный action context),
  MUST быть удалены или переименованы как navigational shortcut.
- Для сохранённых mirror-карточек title/description MUST явно указывать, что
  это mirror, а не primary source of truth.
- Secondary mirror-карточки MUST NOT добавлять dashboard-to-dashboard links,
  если такой target уже доступен через top-level шину.
- Если зеркало добавляет value (например, provider-scoped breakdown), укажи это
  в description без дублирования navigation link.

## Legacy-документы

Архивные материалы перемещены в `docs/03-guides/dashboards/legacy/`.

Они могут содержать устаревшие переменные (`$run-id`, `execution`) и старые формулы.


## Regenerate and verify parity

Для регенерации инвентаризации dashboard metadata (UID/title/variables/links/tags):

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --json
```

Для проверки parity с каноническими документами (`variables-guide.md`, `monitoring-index.md`)
и mandatory links contract:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
```

Для локального health rollup shipped dashboards:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --health-summary --json
```

Для drift check против exported/deployed snapshot directory:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --deployed-dir /path/to/grafana-exports --check --json
```

CI gate запускает эту проверку в `docs.yml` и фейлит pipeline при расхождении
канонических полей.
