______________________________________________________________________

Version: 1.0.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Monitoring Docs Index

## Incident-Time Operator Index

Use this page first when the symptom family is unclear. It is intentionally
short; detailed setup, metric contracts, and dashboard extension rules live in
the linked owner docs.

| Question / symptom | Open first | Then use | Owner doc |
| ------------------ | ---------- | -------- | --------- |
| What is currently broken or degraded, and where should I drill down first? | `bioetl-overview-v2` | `System Status` + `Next Action`, then `2. Runtime`, `4. Data Quality`, `3. Provider Health`, `Control Plane / Replay Safety`, or `6. Workflow Overview` based on the status reason | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Did runtime health, logs, memory, or alert-condition panels regress? | `bioetl-runtime` | `bioetl diagnostics guide`; [Observability Checklist](../../05-operations/runbooks/observability-checklist.md) | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Is a provider slow, degraded, or exhausting retries? | `bioetl-provider-health-v2` | `bioetl diagnostics health --json`; provider incident runbook | [Incident Response](../../05-operations/runbooks/incident-response.md) |
| Is DQ quality/freshness/quarantine unhealthy? | `bioetl-dq-v2` | `bioetl diagnostics quarantine --pipeline <pipeline>` | [DQ Failure Investigation](../../05-operations/runbooks/dq-failure-investigation.md) |
| Which exact Silver-filtered record failed and why? | `bioetl-silver-reject-explorer` | `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only ...` | [Quarantine Management](../../05-operations/runbooks/quarantine-management.md) |
| Can replay/resume be trusted for the selected pipeline/run_type/time range? | `bioetl-control-plane-v1` | `Replay / Resume Blockers`, then `bioetl checkpoint inspect ...`; `bioetl checkpoint audit-run ...` | [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md) |
| Are declarative workflow steps failing or skipping? | `bioetl-workflow-overview` | workflow runner metrics via `bioetl_workflow_*` | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Is the metric/rule/dashboard vocabulary drifting? | inventory helper | `python -m scripts.engineering.qa report-observability-metric-inventory --json` | [Observability Metrics Contract](../../04-reference/contracts/observability.md) |

Boundary rule: Prometheus/Grafana answer aggregate operational questions.
Record-level forensics, exact replay evidence, and per-run identifiers belong
in manifest/ledger/CLI/explorer surfaces, not Prometheus labels.


## If X symptom → open dashboard Y → panel Z

| Symptom (X) | Dashboard (Y) | Panel (Z) |
| --- | --- | --- |
| "What is broken/degraded right now?" | `bioetl-overview-v2` | `System Status`, then `Next Action` |
| Runtime failures / lag / blockers | `bioetl-runtime` | `Runtime Blockers / 15m`, `Worst Stage Lag / 15m` |
| Provider degradation or retry exhaustion | `bioetl-provider-health-v2` | `Current Provider Health Status`, `Retries Exhausted by Provider / Operation` |
| DQ deterioration / quarantine growth | `bioetl-dq-v2` | `Data Quality Score (Volume-weighted)`, `Records Quarantined` |
| Need exact rejected record (Silver filter) | `bioetl-silver-reject-explorer` | `Main records table` (row-level drilldown by `payload_hash`) |
| Replay/resume trust issues | `bioetl-control-plane-v1` | `Replay / Resume Blockers` |
| Workflow steps failed/skipped | `bioetl-workflow-overview` | `Failed Workflow Runs`, `Step Outcomes by Kind` |

## Dashboard UX KPIs

Use these UX KPIs as mandatory acceptance checks after any dashboard UX change.

- **time-to-first-action**: elapsed time from opening `bioetl-overview-v2` to
  first correct operator handoff (Runtime, Provider Health, Data Quality, Control
  Plane / Replay Safety, Workflow Overview, or Explore link).
- **click-depth to root cause**: number of clicks required to reach a panel,
  link, or evidence surface that identifies the likely incident root cause.
- **first-hop accuracy from Overview**: share of incident scenarios where the
  first selected link/action in `1. Overview` leads to the correct L1 dashboard
  or evidence surface without corrective backtracking.

### Manual acceptance check (required)

For every navigation UX change, run and record this manual check:

1. Start on `bioetl-overview-v2` default window (`now-12h`, refresh `30s`).
2. Validate **time-to-first-action**: operator identifies and executes the first correct handoff from `System Status`/`Next Action` within target SLA.
3. Validate **click-depth**: likely root-cause surface is reached in **<= 2 clicks** for common runtime/control-plane/dq incidents.
4. Validate fallback path: less frequent actions are reachable via collapsed `Additional Navigation & Forensics` row without broken links or scope leakage.

Record outcome in change notes as: `pass/fail`, measured time-to-first-action, measured click-depth, and incident pattern used.

## First 2 clicks scenario (overview-first)

- Click 1: open `bioetl-overview-v2` and read `System Status` + `Next Action`.
- Click 2: follow recommended top-level route (`2. Runtime`, `Control Plane v1`, `4. Data Quality`) or expand `Additional Navigation & Forensics` for `Provider Health`/`Workflow`/`Explore`.

## Architecture Map

| Layer / surface | Responsibility | Source of truth |
| --------------- | -------------- | --------------- |
| Domain port | Transport-neutral metrics/tracing/logging contracts | `src/bioetl/domain/ports/observability/` |
| Application emitters | Stage, DQ, control-plane, and workflow metric callsites through injected ports | `src/bioetl/application/**` |
| Infrastructure adapter | Prometheus object registry, label normalization, and exposition/push bridge | `src/bioetl/infrastructure/observability/` |
| Composition | Metrics server startup, Pushgateway publication/cleanup, diagnostics service assembly | `src/bioetl/composition/observability_api.py` |
| Grafana dashboards | Operator panels, variables, links, and Explore handoffs | `grafana/dashboards/*.json` |
| Prometheus rules | Alert/recording-rule behavior consumed by dashboards and runbooks | `grafana/prometheus-rules/bioetl_observability.yml` |
| Contracts/docs | Metric vocabulary, label policy, operator routing, and runbook ownership | `docs/04-reference/contracts/observability.md` |

## Канонические источники

1. `grafana/dashboards/*.json` — фактическая конфигурация Grafana и финальный source of truth по panels/links/variables.
1. `docs/03-guides/dashboards/dashboard-v2-usage.md` — короткий операторский сценарий: какой dashboard открыть первым, куда смотреть, как делать drilldown.
1. `docs/03-guides/dashboards/variables-guide.md` — фактические template variables и их PromQL sources.
1. `docs/03-guides/dashboards/dashboard-extension-human.md` — краткое руководство для человека, который расширяет shipped dashboards.
1. `docs/03-guides/dashboards/dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента: JSON invariants, nav model, docs cascade, verification.
1. `docs/03-guides/dashboards/dashboard-v2-updates.md` — bounded audit/change log по shipped JSON.
1. `docs/05-operations/01-monitoring-guide.md` — operational runbook: alert-backed troubleshooting path и ссылки на runbooks.
1. `grafana/README.md` — setup/reference документ по стеку Prometheus/Grafana/Loki/Tempo, а не основной operator quick-start.

## Как читать этот набор

- Для ежедневной работы: начните с `dashboard-v2-usage.md`, потом при необходимости откройте `01-monitoring-guide.md`.
- Для проверки filters и variable sources: используйте `variables-guide.md`.
- Для изменения dashboard человеком: используйте `dashboard-extension-human.md`.
- Для изменения dashboard через AI/LLM: используйте `dashboard-extension-llm.md`.
- Для понимания, что именно недавно менялось в JSON: используйте `dashboard-v2-updates.md`.
- Для инфраструктурной настройки, provisioning и metric catalog: используйте `grafana/README.md`.

## Примечание

Архивные файлы перенесены в `docs/03-guides/dashboards/legacy/` и могут описывать устаревшие переменные (`$run-id`, `execution`) или старые метрики.

Текущий `bioetl-overview-v2` является L0 answer-first точкой входа. Он отвечает
только на вопрос, что сейчас broken/degraded и какой drilldown открыть первым:
`2. Runtime`, `4. Data Quality`, `3. Provider Health`,
`Control Plane / Replay Safety` или
`6. Workflow Overview`. Ответ начинается с `System Status` / `Next Action`;
зелёный `OK` не выводится без recent activity, а backlog/lag cards показывают
culprit stage. Deep DQ/provider/control-plane/forensic диагностика остаётся в
соответствующих L1/L2 dashboards и explorer surfaces.

`bioetl-control-plane-v1` теперь является `Control Plane / Replay Safety`
surface с answer-first `Trust Summary` в самом верху: replay safety state,
checkpoint freshness proxy и ledger/manifest consistency. В этом же верхнем
блоке явно отображается список `Known Blind Spots` (что пока не
инструментировано), чтобы оператор не трактовал отсутствие сигнала как `OK`.

GLOBAL read-path panels остаются отдельно в блоке
`Global diagnostics (non-pipeline scoped)` и не фильтруются по `$pipeline` /
`$run_type`.

`bioetl-runtime` считается канонической triage-точкой для runtime hygiene:
warnings, unstructured logs, adaptive-memory signals и Prometheus-backed alert
conditions. Он не
заменяет `overview`/`dq`/`provider-health`, а собирает log+alert surface в одном
месте для быстрого расследования.

Runtime alert-condition summary панели используют recording-rule series
`bioetl_runtime_alert_condition_*`, чтобы поддерживать согласованность с alert
логикой и уменьшать сложность dashboard JSON.

Для incident drilldown канонический handoff теперь идёт через shipped Explore
links в `bioetl-overview-v2`, `bioetl-dq-v2`, `bioetl-runtime` и
`bioetl-provider-health-v2`: Loki для logs, Tempo для traces, с сохранением
текущего time range. Loki handoff остаётся generic `{job="bioetl"}`, а Tempo
handoff теперь открывается с contextual TraceQL filters по текущему dashboard
scope.
