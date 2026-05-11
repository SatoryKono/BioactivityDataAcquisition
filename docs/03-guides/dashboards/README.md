______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-13'

______________________________________________________________________

# Dashboards Docs Index

Дата сверки: **2026-04-13**
Источник истины: `grafana/dashboards/*.json`

## Актуальные документы

- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе, включая runtime adaptive-memory triage.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `variable-reference.md` — человеческий contract для shipped dashboard variables: role, fallback, scope, propagation.
- `selector-architecture.md` — selector taxonomy, dashboard families, hidden handoff model и future execution-selector design.
- `dashboard-v2-updates.md` — что именно проверено и исправлено в JSON.

Текущий shipped Explore handoff:

- Loki использует безопасный baseline `{job="bioetl"}`.
- Tempo использует contextual TraceQL filters по текущему dashboard scope (`pipeline/run_type` или `provider`).
- `bioetl-runtime` остаётся Prometheus-first в tracing-off режиме: Loki log-hygiene panels теперь живут в collapsed row `Tracing-only Log Hygiene`, а базовый triage path не требует Loki/Tempo datasource.
- Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor
  `0` to `bioetl_runtime_pipeline_run_type_universe`, GLOBAL provider handoff
  anchors `0` to `bioetl_provider_current_status`, and missing scope remains
  `UNKNOWN`. Unstructured Loki hygiene renders parsed `.__error__`, not the
  template function form.

Текущая навигационная модель:

- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow` образуют единую top-level шину.
- На каждой странице navigation panel `id=1000` визуально показывает полный bus `0..5`; текущий dashboard рендерится как disabled dark-gray item, а machine-readable `panel.links` сохраняют omit-self contract.
- Каноническая shipped surface этой шины — text navigation panel `id=1000`;
  root `dashboard.links[]` не обязаны дублировать те же handoff в header row
  рядом с Grafana variables.
- Любые дублирующие dashboard-to-dashboard ссылки из одного dashboard в один
  target dashboard запрещены: переход должен быть ровно один.
- Во всех shipped navigation panels `id=1000` после bus `0..5` закреплены
  global adjunct links: `Silver Reject Explorer`, `Explore Logs`,
  `Explore Traces`.
- `Explore Traces` остаётся optional adjunct surface и считается доступным
  только для traced runs; если runtime использовал `NoOpTracing`, пустой Tempo
  result считается корректным поведением.
- Shipped `Explore Traces` handoff opens the explicit search-first Tempo route,
  bounds the initial window to `now-150m..now`, pins `var-ds=tempo`, and uses
  `var-groupBy=resource.service.name` so Tempo metrics queries stay under the
  local limit and empty trace stores fail closed as empty search results
  instead of invalid breakdown-state queries.
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

`bioetl-overview-v2` is the L0 answer-first surface. It answers one question:
what is currently broken or degraded in BioETL, and where should the operator
drill down first? The first visible answer is now a compact L0/L1 row:
`System Status`, `Next Action`, and `L0 Inputs`. The next visible row keeps
current subsystem summaries (`Runtime Blockers`, `DQ Status`,
`Gold Lifecycle`, `Control Plane`), while provider/workflow
scope is explicit via `Provider Global`, `Workflow Selected`, and
`Workflow Global`. Historical evidence is isolated under the collapsed
`Range Evidence` row, and diagnostics routing lives under the collapsed
`Diagnostics & Docs (Logs / Traces / Raw Metrics)` row.

`bioetl-control-plane-v1` is the `0. Control Plane` surface. It
now starts with an answer-first **Trust Summary** block: replay safety state,
checkpoint freshness gap, ledger/manifest consistency, and telemetry presence
for the selected pipeline scope. Replay/checkpoint panels route to
`checkpoint-debugging.md`, while manifest/ledger evidence panels route to
`run-manifest-inspection.md`. **Known Blind Spots** and terminal-event
evidence live below fold in collapsed incident rows, not in the first-screen
trust block.

Global lookup/read-path panels stay separated in a dedicated
**Global diagnostics (non-pipeline scoped)** block and MUST remain unfiltered by
`$pipeline` / `$run_type`.

`bioetl-runtime`, `bioetl-provider-health-v2`, and `bioetl-dq-v2` are now
answer-first L2 incident surfaces. Their first visible rows use canonical
current-status recording rules (`bioetl_runtime_current_status`,
`bioetl_provider_current_status`, `bioetl_dq_current_status`) plus reason/cause
tables before any selected-range evidence. Range counters, trends, raw tables,
Silver reject breakdowns, logs, and traces stay below the first-screen answer
row or in collapsed diagnostic rows.

## KPI ownership (canonical vs mirrors)

Правило: KPI имеет один canonical dashboard (источник ответа) и может иметь
secondary mirrors только как локальный контекст. Mirror-карточки не должны
добавлять dashboard-to-dashboard links, если такой target уже есть в top-level
шине.

| KPI | Canonical dashboard | Secondary mirrors |
| --- | --- | --- |
| System Status | `1. Overview` | `2. Runtime`, `0. Control Plane`, `5. Workflow` |
| Next Action | `1. Overview` | `2. Runtime`, `3. Provider Health` |
| L0 Inputs | `1. Overview` | `2. Runtime`, `4. Data Quality`, `0. Control Plane` |
| Gold Lifecycle | `1. Overview` | `2. Runtime`, `0. Control Plane` |
| Provider Global | `1. Overview` | `3. Provider Health` |
| Workflow Selected | `1. Overview` | `5. Workflow` |
| Workflow Global | `1. Overview` | `5. Workflow` |
| Replay Safety State | `0. Control Plane` | `1. Overview`, `2. Runtime` |
| Checkpoint Freshness Proxy | `0. Control Plane` | `2. Runtime` |
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
