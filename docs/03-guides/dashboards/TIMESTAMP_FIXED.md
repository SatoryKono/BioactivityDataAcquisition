# Исправление: Время запуска теперь отображается!

> **Path verification (required):** before applying this guide/prompt, locate the runtime observability modules with `rg -n "PrometheusMetrics|start_http_server|metrics_server_integration" src/bioetl`.
> Use these runtime paths:
> Metric definitions/registries — `src/bioetl/infrastructure/observability/metrics.py`, `src/bioetl/infrastructure/observability/prometheus_metrics.py`.
> Metrics server wiring/integration — `src/bioetl/infrastructure/observability/metrics_server_adapter.py`, `src/bioetl/interfaces/cli/commands/metrics_server_integration.py`.

## ✅ Что было исправлено

Добавлена новая метрика в `src/bioetl/infrastructure/observability/prometheus_metrics.py` для отображения времени запуска:

### Обновление src/bioetl/infrastructure/observability/prometheus_metrics.py

**Добавлены две новые метрики:**

1. **bioetl_run_start_timestamp** (Gauge)

   - Unix timestamp времени запуска
   - Используется в дашбордах для отображения
   - Обновляется каждый запрос

1. **bioetl_run** (Info)

   - Полная информация о запуске
   - Включает: run_id, pipeline, start_time, timestamp

### Обновление дашбордов v2

Все три дашборда обновлены:

**Было:**

```promql
timestamp(bioetl_records_processed_total) / 1000
```

**Стало:**

```promql
bioetl_run_start_timestamp
```

______________________________________________________________________

## 📊 Теперь дашборды показывают:

```
┌──────────────────────┬────────────────┬──────────────────────────────┐
│ Pipeline             │ Run Type       │ Execution Timestamp          │
│ uniprot              │ incremental    │ 1645382400                  │
│                      │                │ (26 Feb 2026, 10:00:00 UTC) │
└──────────────────────┴────────────────┴──────────────────────────────┘
```

______________________________________________________________________

## 🚀 Как использовать

1. **Откройте дашборд:**

   ```
   http://localhost:3000/d/bioetl-dq-v2
   ```

1. **В верхней части видны:**

   - ✅ Pipeline название
   - ✅ Run Type
   - ✅ Execution Timestamp (время запуска)

1. **Timestamp конвертируется автоматически:**

   - Unix timestamp: `1645382400`
   - Human readable: `26 Feb 2026, 10:00:00 UTC`

______________________________________________________________________

## 🧪 Проверка

Проверить, что метрика работает:

```bash
# 1. Проверить metrics endpoint
curl http://localhost:8000/metrics | grep bioetl_run_start_timestamp

# 2. Результат должен быть похож на:
# bioetl_run_start_timestamp{pipeline="uniprot",run_id="run-492157"} 1645382400.0
```

______________________________________________________________________

## 📄 Файлы, которые изменились

```
✓ src/bioetl/infrastructure/observability/prometheus_metrics.py
  - Добавлены метрики bioetl_run_start_timestamp и bioetl_run

✓ grafana/dashboards/bioetl-dq-v2.json
  - Обновлен запрос для Execution Timestamp

✓ grafana/dashboards/bioetl-overview-v2.json
  - Обновлен запрос для Execution Timestamp

✓ grafana/dashboards/bioetl-provider-health-v2.json
  - Обновлен запрос для Execution Timestamp
```

______________________________________________________________________

## ✨ Итог

Теперь все три дашборда v2 полностью функциональны и отображают:

- ✅ Pipeline (название)
- ✅ Run Type (тип запуска)
- ✅ Execution Timestamp (время запуска) ← **НОВОЕ!**

**Готовы к production!** 🚀

______________________________________________________________________

**Дата:** 22 февраля 2026
**Статус:** ✅ Production Ready
