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
- `dashboard-v2-updates.md` — что именно проверено и исправлено в JSON.

Текущий shipped Explore handoff:

- Loki использует безопасный baseline `{job="bioetl"}`.
- Tempo использует contextual TraceQL filters по текущему dashboard scope (`pipeline/run_type` или `provider`).
- `bioetl-runtime` остаётся Prometheus-first в tracing-off режиме: Loki log-hygiene panels теперь живут в collapsed row `Tracing-only Log Hygiene`, а базовый triage path не требует Loki/Tempo datasource.

Текущая навигационная модель:

- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow` образуют единую top-level шину.
- На каждой странице шина показывает все пункты `0..5`, кроме текущей страницы.
- Любые дублирующие dashboard-to-dashboard ссылки из одного dashboard в один
  target dashboard запрещены: переход должен быть ровно один.
- `Explore Logs` и `Explore Traces` доступны только на `2. Runtime` и
  `4. Data Quality`.
- `Silver Reject Explorer` доступен только на `4. Data Quality`.

`bioetl-overview-v2` is the L0 answer-first surface. It answers one question:
what is currently broken or degraded in BioETL, and where should the operator
drill down first? The first visible answer is now a compact L0/L1 row:
`System Status`, `Next Action`, and `L0 Inputs`. The next visible row keeps
current subsystem summaries (`Runtime Blockers Current`, `DQ Status Current`,
`Gold Lifecycle Current`, `Control Plane Current`), while provider/workflow
scope is explicit via `Provider GLOBAL Scope`, `Workflow Selected Scope`, and
`Workflow GLOBAL Scope`. Historical evidence is isolated under the collapsed
`Range Evidence` row, and diagnostics routing lives under the collapsed
`Diagnostics & Docs` row.

`bioetl-control-plane-v1` is the `0. Control Plane` surface. It
now starts with an answer-first **Trust Summary** block: replay safety state,
checkpoint freshness proxy, and ledger/manifest consistency for the selected
pipeline scope. A visible **Known Blind Spots** list is part of this top block
and documents currently non-instrumented signals.

Global lookup/read-path panels stay separated in a dedicated
**Global diagnostics (non-pipeline scoped)** block and MUST remain unfiltered by
`$pipeline` / `$run_type`.

## KPI ownership (canonical vs mirrors)

Правило: KPI имеет один canonical dashboard (источник ответа) и может иметь
secondary mirrors только как локальный контекст. Mirror-карточки не должны
добавлять dashboard-to-dashboard links, если такой target уже есть в top-level
шине.

| KPI | Canonical dashboard | Secondary mirrors |
| --- | --- | --- |
| System Status | `1. BioETL Overview` | `2. Runtime`, `0. Control Plane`, `5. Workflow` |
| Next Action | `1. BioETL Overview` | `2. Runtime`, `3. Provider Health` |
| L0 Inputs | `1. BioETL Overview` | `2. Runtime`, `4. Data Quality`, `0. Control Plane` |
| Gold Lifecycle Current | `1. BioETL Overview` | `2. Runtime`, `0. Control Plane` |
| Provider GLOBAL Scope | `1. BioETL Overview` | `3. Provider Health` |
| Workflow Selected Scope | `1. BioETL Overview` | `5. Workflow` |
| Workflow GLOBAL Scope | `1. BioETL Overview` | `5. Workflow` |
| Replay Safety State | `0. Control Plane` | `1. BioETL Overview`, `2. Runtime` |
| Checkpoint Freshness Proxy | `0. Control Plane` | `2. Runtime` |
| Ledger/Manifest Consistency | `0. Control Plane` | `2. Runtime` |
| Provider Health (aggregated) | `3. Provider Health` | `1. BioETL Overview`, `2. Runtime` |
| DQ Status (Silver Reject / quality posture) | `4. Data Quality` | `1. BioETL Overview`, `2. Runtime` |

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

CI gate запускает эту проверку в `docs.yml` и фейлит pipeline при расхождении
канонических полей.
