______________________________________________________________________

Version: 1.0.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-13'

______________________________________________________________________

# Monitoring Docs Index

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

Текущий `bioetl-overview-v2` также считается канонической точкой входа для
control-plane и lineage health: manifest writes, ledger appends, checkpoint
compatibility, lineage refs missing, composite source-selection decisions и
lineage fragment outcomes.

Новый `bioetl-control-plane-v1` собирает агрегированные панели по manifest
writes, ledger appends, checkpoint compatibility и read failures. Это dashboard
показывает доли ошибок и предлагает direct link на alert `BioETLControlPlaneReadFailureRate`
(runbook: `docs/05-operations/runbooks/observability-checklist.md`) для быстрого
реагирования на контрольные-plane regressions.

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
