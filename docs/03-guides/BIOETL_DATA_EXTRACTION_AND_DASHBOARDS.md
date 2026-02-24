# BioETL: Извлечение данных и создание дашбордов

**Версия:** 1.0  
**Дата:** 22 февраля 2026  
**Статус:** Production Ready

---

## Содержание

1. [Извлечение данных из BioETL](#извлечение-данных-из-bioetl)
2. [Настройка мониторинга](#настройка-мониторинга)
3. [Создание дашбордов](#создание-дашбордов)
4. [Использование переменных фильтрации](#использование-переменных-фильтрации)
5. [Примеры PromQL запросов](#примеры-promql-запросов)
6. [Troubleshooting](#troubleshooting)

---

## Извлечение данных из BioETL

### Источник метрик

BioETL экспортирует метрики через HTTP endpoint при запуске пайплайна:

```
http://localhost:8000/metrics
```

### Как запустить пайплайн с метриками

```bash
# 1. Убедитесь, что метрики включены в .env
export BIOETL_METRICS_ENABLED=true
export BIOETL_METRICS_PORT=8000

# 2. Запустите пайплайн (любой)
bioetl run --pipeline chembl_activity

# 3. В другом терминале проверьте метрики
curl http://localhost:8000/metrics | head -50
```

### Метрики, которые экспортирует BioETL

**Pipeline метрики (обязательные):**
- `bioetl_pipeline_duration_seconds` (Histogram) — длительность выполнения
- `bioetl_records_processed_total` (Counter) — обработанные записи
- `bioetl_errors_total` (Counter) — количество ошибок
- `bioetl_batch_size_records` (Histogram) — размер батчей
- `bioetl_pipeline_runs_total` (Counter) — количество запусков

**Data Quality метрики:**
- `bioetl_dq_records_quarantined_total` (Counter) — карантинные записи
- `bioetl_dq_validation_score` (Gauge) — оценка валидности
- `bioetl_dq_anomaly_detected` (Counter) — обнаруженные аномалии
- `bioetl_data_freshness_seconds` (Gauge) — свежесть данных

**Health метрики:**
- `bioetl_circuit_breaker_state` (Gauge) — состояние circuit breaker
- `bioetl_health_check_status` (Gauge) — статус здоровья
- `bioetl_provider_health_status` (Gauge) — статус провайдера

**Adapter метрики:**
- `bioetl_adapter_request_duration_seconds` (Histogram) — длительность API запросов
- `bioetl_adapter_requests_total` (Counter) — количество API запросов
- `bioetl_http_request_duration_seconds` (Histogram) — длительность HTTP запросов
- `bioetl_http_retries_total` (Counter) — HTTP retry попытки

[Полный каталог 90+ метрик см. в docs/03-guides/metrics-monitoring.md]

---

## Настройка мониторинга

### Архитектура

```
BioETL App (8000/metrics)
    ↓ (scrape каждые 15 сек)
Prometheus (9090)
    ↓ (PromQL запросы)
Grafana (3000)
    ↓
Дашборды
```

### Быстрый старт

```bash
# 1. Запустить Prometheus и Grafana
docker compose -f docker-compose.monitoring.yml up -d

# 2. Проверить статус
docker compose -f docker-compose.monitoring.yml ps

# 3. Запустить пайплайн
bioetl run --pipeline chembl_activity

# 4. Дождаться первого scrape'а (15 сек)

# 5. Открыть Grafana
http://localhost:3000 (admin/admin)
```

### Конфигурация prometheus.yml

```yaml
global:
  scrape_interval: 15s          # Как часто собирать метрики
  evaluation_interval: 15s      # Как часто вычислять правила

scrape_configs:
  - job_name: 'bioetl'
    static_configs:
      - targets: ['host.docker.internal:8000']  # BioETL metrics endpoint
    metrics_path: /metrics
```

### Конфигурация Grafana

**Datasource (уже настроен):**
- Name: Prometheus
- URL: http://localhost:9090 (для Docker: http://prometheus:9090)
- Access: Server

**Provisioning (автоматический импорт дашбордов):**
- Dashboards загружаются из `grafana/provisioning/dashboards/`
- JSON файлы в `grafana/dashboards/`
- Обновляются каждые 30 сек

---

## Создание дашбордов

### Вариант 1: Через UI Grafana (простой способ)

```
1. Home → Dashboards → New → Create new dashboard
2. Add panel → Time series (или другая визуализация)
3. Выбрать Prometheus как datasource
4. Написать PromQL запрос
5. Customize (заголовок, легенда, оси)
6. Save dashboard
```

### Вариант 2: JSON (для версионирования)

```bash
# 1. Экспортировать из UI
Dashboard → Share (🔗) → Export → Save JSON

# 2. Сохранить в grafana/dashboards/

# 3. Импортировать в другой Grafana
Home → Dashboards → Import → Upload JSON
```

### Шаблон простого дашборда JSON

```json
{
  "dashboard": {
    "title": "My BioETL Dashboard",
    "uid": "my-bioetl-dash",
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "panels": [
      {
        "id": 1,
        "title": "Records Processed",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "rate(bioetl_records_processed_total[5m])",
            "legendFormat": "{{pipeline}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Error Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "rate(bioetl_errors_total[5m])",
            "legendFormat": "{{pipeline}}"
          }
        ]
      }
    ],
    "templating": {
      "list": [
        {
          "name": "pipeline",
          "type": "query",
          "datasource": "Prometheus",
          "definition": "label_values(bioetl_records_processed_total, pipeline)",
          "includeAll": true,
          "multi": true
        }
      ]
    }
  },
  "overwrite": true
}
```

### Рекомендуемые визуализации

| Метрика | Тип графика | Пример |
|---------|-------------|--------|
| Скорость обработки | Timeseries | `rate(bioetl_records_processed_total[5m])` |
| Статус | Stat | `bioetl_circuit_breaker_state` |
| Распределение | Histogram | `bioetl_batch_size_records` |
| Процент | Gauge | `bioetl_dq_validation_score * 100` |
| Таблица | Table | Результаты с label'ами |

---

## Использование переменных фильтрации

### Зачем нужны переменные

Переменные позволяют фильтровать данные без редактирования PromQL:

```
Pipeline: [All ▼]  Run ID: [All ▼]

Выберите → все панели обновляются
```

### Как добавить переменную в дашборд

**UI способ:**
```
Dashboard Settings → Variables → Add variable
- Name: pipeline
- Type: Query
- Data source: Prometheus
- Query: label_values(bioetl_records_processed_total, pipeline)
- Include All: true
- Multi: true
```

**JSON способ:**
```json
"templating": {
  "list": [
    {
      "name": "pipeline",
      "type": "query",
      "datasource": "Prometheus",
      "definition": "label_values(bioetl_records_processed_total, pipeline)",
      "includeAll": true,
      "multi": true,
      "refresh": 1,
      "sort": 1
    },
    {
      "name": "run_id",
      "type": "query",
      "datasource": "Prometheus",
      "definition": "label_values(bioetl_records_processed_total{pipeline=~\"$pipeline\"}, run_id)",
      "includeAll": true,
      "multi": true,
      "refresh": 1,
      "sort": 1
    }
  ]
}
```

### Использование переменных в PromQL

```promql
# Использовать переменную в запросе
bioetl_records_processed_total{pipeline=~"$pipeline", run_id=~"$run_id"}

# Регулярное выражение (любое значение)
pipeline=~".*"

# Конкретное значение
pipeline="chembl"
```

---

## Примеры PromQL запросов

### Pipeline Metrics

**Скорость обработки записей (records/sec):**
```promql
rate(bioetl_records_processed_total{pipeline="$pipeline"}[5m])
```

**Текущее количество обработанных записей:**
```promql
sum(bioetl_records_processed_total{pipeline="$pipeline"})
```

**95-й перцентиль длительности пайплайна:**
```promql
histogram_quantile(0.95, rate(bioetl_pipeline_duration_seconds_bucket[5m]))
```

**Процент ошибок:**
```promql
sum(rate(bioetl_errors_total[5m])) / sum(rate(bioetl_records_processed_total[5m])) * 100
```

### Data Quality Metrics

**Процент карантинных записей:**
```promql
sum(rate(bioetl_dq_records_quarantined_total[5m])) / 
sum(rate(bioetl_records_processed_total[5m])) * 100
```

**Validation score по pipeline:**
```promql
bioetl_dq_validation_score{pipeline="$pipeline"}
```

**Аномалии по типу:**
```promql
sum(rate(bioetl_dq_anomaly_detected[1h])) by (anomaly_type)
```

### Health Metrics

**Circuit Breaker статус (0=closed, 1=half-open, 2=open):**
```promql
bioetl_circuit_breaker_state{adapter="$adapter"}
```

**Health статус компонентов:**
```promql
bioetl_health_check_status
```

**Provider response time (P95):**
```promql
histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket[5m]))
```

### Adapter Metrics

**HTTP retry rate:**
```promql
rate(bioetl_http_retries_total[5m])
```

**Request success rate:**
```promql
sum(rate(bioetl_adapter_requests_total{status=~"2.."}[5m])) / 
sum(rate(bioetl_adapter_requests_total[5m])) * 100
```

---

## Troubleshooting

### Метрики не появляются в Prometheus

**Проблема:** Target DOWN в http://localhost:9090/targets

**Решение:**
```bash
# 1. Проверить что пайплайн запущен
# (консоль должна показывать "Metrics server running on...")

# 2. Проверить что метрики доступны
curl http://localhost:8000/metrics | head -20

# 3. Проверить prometheus.yml
# targets должен быть: ['host.docker.internal:8000']

# 4. Если на Linux, добавить флаг при запуске Prometheus
docker run --add-host=host.docker.internal:host-gateway ...
```

### Дашборд пуст (No data)

**Проблема:** "No data to show"

**Решение:**
```bash
# 1. Проверить что выбран правильный pipeline
# (выпадающее меню Pipeline)

# 2. Проверить что пайплайн работал достаточно долго
# (метрики появляются не сразу)

# 3. Проверить PromQL запрос
# Home → Explore → ввести запрос

# 4. Увеличить временной диапазон
# "Last 6 hours" → "Last 24 hours"

# 5. Убедиться что Run ID соответствует Pipeline
# (если использовать зависимые переменные)
```

### Prometheus медленно грузит данные

**Проблема:** Долгое время загрузки графиков

**Решение:**
```bash
# 1. Уменьшить retention period
# Редактировать prometheus.yml: retention: 7d (вместо 15d)

# 2. Уменьшить количество метрик в запросе
# Вместо: bioetl_records_processed_total{} by (pipeline, stage, status)
# Использовать: bioetl_records_processed_total{pipeline="$pipeline"}

# 3. Увеличить scrape_interval (если метрики не критичны)
# scrape_interval: 30s (вместо 15s)

# 4. Перезапустить Prometheus
docker restart bioetl-prometheus
```

### Переменные не обновляются

**Проблема:** Выбор Pipeline не меняет Run ID

**Решение:**
```bash
# 1. Проверить что Run ID переменная зависит от Pipeline
# Dashboard Settings → Variables → run_id
# Убедитесь: definition = "label_values(...{pipeline=~\"$pipeline\"}...)"

# 2. Обновить страницу дашборда (F5)

# 3. Убедитесь что refresh установлен на 1 (на изменение переменной)
```

---

## Быстрая справка

### Команды Docker

```bash
# Запустить мониторинг
docker compose -f docker-compose.monitoring.yml up -d

# Просмотреть логи
docker compose -f docker-compose.monitoring.yml logs -f

# Остановить
docker compose -f docker-compose.monitoring.yml down
```

### Основные URL

| Сервис | URL |
|--------|-----|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |
| BioETL Metrics | http://localhost:8000/metrics |
| Prometheus Targets | http://localhost:9090/targets |
| Grafana Explore | http://localhost:3000/explore |

### Файлы конфигурации

| Файл | Назначение |
|------|-----------|
| `grafana/prometheus.yml` | Конфиг Prometheus (targets, scrape interval) |
| `docker-compose.monitoring.yml` | Docker Compose для мониторинга |
| `grafana/dashboards/` | JSON дашборды |
| `grafana/provisioning/` | Provisioning конфиги |

---

## Документация

- **grafana/README.md** — быстрый старт
- **docs/05-operations/01-monitoring-guide.md** — полный гайд
- **docs/03-guides/metrics-monitoring.md** — каталог метрик
- **docs/03-guides/dashboards/** — документация по дашбордам

---

**Версия:** 1.0  
**Статус:** Production Ready  
**Дата:** 22 февраля 2026
