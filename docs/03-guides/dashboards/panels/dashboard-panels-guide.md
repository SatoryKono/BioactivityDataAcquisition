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

Полная документация всех панелей требует анализа JSON файлов dashboards в `grafana/dashboards/`.
Текущая документация предоставляет базовую информацию для ключевых dashboards.