# Dashboard Panels Documentation

Этот каталог содержит детальную документацию панелей для Grafana dashboards BioETL.

## Структура документации

Каждый dashboard имеет отдельный документ с описанием всех панелей:

- `bioetl-overview-v2-panels.md` - Overview dashboard
- `bioetl-control-plane-v1-panels.md` - Control Plane dashboard
- `bioetl-dq-v2-panels.md` - Data Quality dashboard
- `bioetl-provider-health-v2-panels.md` - Provider Health dashboard
- `bioetl-runtime-panels.md` - Runtime dashboard
- `bioetl-silver-reject-explorer-panels.md` - Silver Reject Explorer dashboard
- `bioetl-workflow-overview-panels.md` - Workflow Overview dashboard
- `bioetl-alerts-slo-panels.md` - Alerts SLO dashboard

## Шаблон документации панели

Для каждой панели документируется:

1. **Название панели** - идентификатор в Grafana
2. **Тип визуализации** - graph, stat, table, heatmap и т.д.
3. **Назначение** - что показывает панель
4. **Источники данных** — фактический datasource: Prometheus metric family,
   Quarantine Explorer HTTP endpoint, Loki или Grafana metadata. HTTP-backed
   identity/forensic panels нельзя документировать как Prometheus panels.
5. **Формулы/запросы** - PromQL запросы
6. **Фильтры/переменные** - какие переменные Grafana используются
7. **Пороги/алерты** - если есть

## Примечание

Shipped dashboard JSON in `grafana/dashboards/` remains the source of truth.
All shipped dashboards now provide 1:1 panel inventory coverage:

- `bioetl-overview-v2-panels.md` - 1:1 panel inventory
- `bioetl-control-plane-v1-panels.md` - 1:1 panel inventory
- `bioetl-dq-v2-panels.md` - 1:1 panel inventory
- `bioetl-provider-health-v2-panels.md` - 1:1 panel inventory
- `bioetl-runtime-panels.md` - 1:1 panel inventory
- `bioetl-silver-reject-explorer-panels.md` - 1:1 panel inventory
- `bioetl-workflow-overview-panels.md` - 1:1 panel inventory
- `bioetl-alerts-slo-panels.md` - 1:1 panel inventory
