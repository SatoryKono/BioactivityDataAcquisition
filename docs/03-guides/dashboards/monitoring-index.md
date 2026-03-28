# Monitoring Docs Index

## Канонические источники

1. `grafana/dashboards/*.json` — фактическая конфигурация Grafana и финальный source of truth по panels/links/variables.
2. `docs/03-guides/dashboards/dashboard-v2-usage.md` — короткий операторский сценарий: какой dashboard открыть первым, куда смотреть, как делать drilldown.
3. `docs/03-guides/dashboards/variables-guide.md` — фактические template variables и их PromQL sources.
4. `docs/03-guides/dashboards/dashboard-v2-updates.md` — bounded audit/change log по shipped JSON.
5. `docs/05-operations/01-monitoring-guide.md` — operational runbook: alert-backed troubleshooting path и ссылки на runbooks.
6. `grafana/README.md` — setup/reference документ по стеку Prometheus/Grafana/Loki/Tempo, а не основной operator quick-start.

## Как читать этот набор

- Для ежедневной работы: начните с `dashboard-v2-usage.md`, потом при необходимости откройте `01-monitoring-guide.md`.
- Для проверки filters и variable sources: используйте `variables-guide.md`.
- Для понимания, что именно недавно менялось в JSON: используйте `dashboard-v2-updates.md`.
- Для инфраструктурной настройки, provisioning и metric catalog: используйте `grafana/README.md`.

## Примечание

Архивные файлы перенесены в `docs/03-guides/dashboards/legacy/` и могут описывать устаревшие переменные (`$run-id`, `execution`) или старые метрики.

Текущий `bioetl-overview-v2` также считается канонической точкой входа для
control-plane и lineage health: manifest writes, ledger appends, checkpoint
compatibility и lineage fragment outcomes.

Для incident drilldown канонический handoff теперь идёт через shipped Explore
links в `bioetl-overview-v2`, `bioetl-dq-v2` и `bioetl-provider-health-v2`:
Loki для logs, Tempo для traces, с сохранением текущего time range.
