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
4. **Источники данных** - какие Prometheus метрики используются
5. **Формулы/запросы** - PromQL запросы
6. **Фильтры/переменные** - какие переменные Grafana используются
7. **Пороги/алерты** - если есть

## Примечание

Shipped dashboard JSON in `grafana/dashboards/` remains the source of truth.
Panel-doc coverage can vary by dashboard family:

- `bioetl-control-plane-v1-panels.md` and
  `bioetl-workflow-overview-panels.md` now provide 1:1 panel inventory
  coverage for the shipped JSON pages;
- other dashboard pages may still be summary-level and should be expanded with
  the same template when forensic panel-by-panel documentation is required.
