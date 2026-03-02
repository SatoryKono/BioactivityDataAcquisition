# BioETL Dashboard — Примеры кастомизации

## Содержание
1. [Добавить новую метрику](#добавить-новую-метрику)
2. [Создать пользовательский дашборд](#создать-пользовательский-дашборд)
3. [Настроить Alert](#настроить-alert)
4. [Использовать переменные фильтров](#использовать-переменные-фильтров)
5. [Экспортировать/Импортировать дашборды](#экспортироватьимпортировать-дашборды)

---

## Добавить новую метрику

### Шаг 1: Определить метрику в metrics-server.py

```python
# Добавить в начало файла
from prometheus-client import Counter, Gauge, Histogram

# Новая метрика: количество активных run
ACTIVE-RUNS = Gauge(
    'bioetl-active-runs',
    'Number of active pipeline runs'
)

# Метрика: время ответа API
API-RESPONSE-TIME = Histogram(
    'bioetl-api-response-seconds',
    'API response time in seconds',
    ['endpoint', 'method']
)

# Метрика: ошибки по типам
ERRORS-BY-TYPE = Counter(
    'bioetl-errors-total',
    'Total errors by type',
    ['error-type', 'pipeline']
)
```

### Шаг 2: Генерировать данные метрик

```python
def -generate-synthetic-metrics(self):
    """Generate synthetic BioETL metrics."""
    # ... существующий код ...
    
    # Добавить новые метрики
    ACTIVE-RUNS.set(random.randint(3, 8))
    
    # API response time
    for endpoint in ['/fetch', '/process', '/validate']:
        for method in ['GET', 'POST']:
            API-RESPONSE-TIME.labels(
                endpoint=endpoint,
                method=method
            ).observe(random.uniform(0.1, 2.0))
    
    # Errors by type
    for error-type in ['validation-error', 'network-error', 'timeout']:
        for pipeline in ['uniprot', 'pubmed', 'pubchem']:
            ERRORS-BY-TYPE.labels(
                error-type=error-type,
                pipeline=pipeline
            ).inc(random.randint(0, 5))
```

### Шаг 3: Перезапустить metrics-server.py

```bash
pkill -f metrics-server.py
python ./metrics-server.py &
```

### Шаг 4: Дождаться scrape и использовать в Grafana

```bash
# Проверить, что метрика доступна
curl http://localhost:8000/metrics | grep bioetl-active-runs
# Output: bioetl-active-runs 5.0
```

### Шаг 5: Добавить панель в дашборд

```
1. Grafana → Dashboard → Edit
2. Add panel → New visualization
3. Prometheus query:
   bioetl-active-runs
   или
   avg(bioetl-api-response-seconds) by (endpoint)
4. Customize title, legend, colors
5. Save dashboard
```

---

## Создать пользовательский дашборд

### Способ A: Через UI (без кода)

**Пример: Дашборд "Pipeline Performance"**

```
1. Home → Dashboards → New → Create new dashboard
2. Add panel → Time series
   Name: "Records per Pipeline"
   Query: sum(rate(bioetl-records-processed-total[5m])) by (pipeline)
   Legend: {{pipeline}}
   
3. Add panel → Stat
   Name: "Error Rate"
   Query: avg(bioetl-error-rate)
   Thresholds: Green <5%, Orange <10%, Red >10%
   
4. Add panel → Gauge
   Name: "Quality Score"
   Query: sum(bioetl-records-processed-total{stage="gold"}) / sum(bioetl-records-processed-total{stage="bronze"})
   Min: 0, Max: 1
   
5. Dashboard settings → Save as "Pipeline Performance"
```

### Способ B: JSON (для版контроля + повторного использования)

**Создать файл: custom-dashboard.json**

```json
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "gnetId": null,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "panels": [
    {
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "custom": {},
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 2,
      "options": {
        "legend": {
          "calcs": ["last"],
          "displayMode": "table",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "multi"
        }
      },
      "targets": [
        {
          "expr": "sum(rate(bioetl-records-processed-total[5m])) by (pipeline)",
          "legendFormat": "{{pipeline}}",
          "refId": "A"
        }
      ],
      "title": "Throughput by Pipeline",
      "type": "timeseries"
    },
    {
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [],
          "thresholds": {
            "mode": "percentage",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "yellow",
                "value": 50
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "percent"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 3,
      "options": {
        "orientation": "auto",
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        },
        "showThresholdLabels": false,
        "showThresholdMarkers": true
      },
      "targets": [
        {
          "expr": "avg(bioetl-error-rate) * 100",
          "refId": "A"
        }
      ],
      "title": "Average Error Rate",
      "type": "gauge"
    }
  ],
  "refresh": "10s",
  "schemaVersion": 30,
  "style": "dark",
  "tags": ["bioetl", "custom", "performance"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Pipeline Performance",
  "uid": "custom-performance",
  "version": 0
}
```

**Импортировать в Grafana:**

```bash
# Способ 1: Через UI
# Home → Dashboards → Import
# Загрузить custom-dashboard.json
# Select Prometheus data source
# Import

# Способ 2: Через provisioning (автоматическое при старте)
cp custom-dashboard.json ./grafana/dashboards/
# Перезапустить: docker restart bioetl-grafana
```

---

## Настроить Alert

### Способ A: Через UI (простой)

```
1. Dashboard → Alert rules (звоночек 🔔)
2. Create alert rule → Prometheus
3. Condition:
   Query A: avg(bioetl-error-rate)
   If: A > 0.1 (10%)
4. Duration: 5m (alert если больше 5 минут)
5. Notification channel: Email/Slack/PagerDuty
6. Save
```

### Способ B: Через Prometheus alerts (advanced)

**Редактировать grafana/prometheus.yml:**

```yaml
global:
  scrape-interval: 15s
  evaluation-interval: 15s

rule-files:
  - /etc/prometheus/alerts.yml

alerting:
  alertmanagers:
    - static-configs:
        - targets:
            - alertmanager:9093

scrape-configs:
  - job-name: 'bioetl'
    static-configs:
      - targets: ['host.docker.internal:8000']
```

**Создать файл grafana/alerts.yml:**

```yaml
groups:
  - name: bioetl-alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: avg(bioetl-error-rate) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: RecordsNotProcessing
        expr: increase(bioetl-records-processed-total[5m]) == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "No records processed in 10 minutes"
          description: "Pipeline might be stuck"

      - alert: SlowProcessing
        expr: histogram-quantile(0.95, rate(bioetl-processing-duration-seconds-bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Processing is slow"
          description: "P95 latency is {{ $value }}s"
```

---

## Использовать переменные фильтров

### Пример: Добавить фильтр по датам

**В JSON дашборда добавить переменную:**

```json
{
  "templating": {
    "list": [
      {
        "allValue": null,
        "current": {
          "selected": false,
          "text": "now-1h",
          "value": "now-1h"
        },
        "hide": 0,
        "includeAll": false,
        "label": "Time Range",
        "multi": false,
        "name": "time-range",
        "options": [
          {"text": "Last hour", "value": "now-1h"},
          {"text": "Last 6 hours", "value": "now-6h"},
          {"text": "Last 24 hours", "value": "now-24h"},
          {"text": "Last 7 days", "value": "now-7d"}
        ],
        "query": "now-1h, now-6h, now-24h, now-7d",
        "sort": 0,
        "tagValuesQuery": "",
        "tags": [],
        "type": "custom"
      },
      {
        "allValue": null,
        "current": {},
        "datasource": "Prometheus",
        "definition": "label-values(bioetl-records-processed-total, stage)",
        "hide": 0,
        "includeAll": true,
        "label": "Stage",
        "multi": true,
        "name": "stage",
        "options": [],
        "query": {
          "query": "label-values(bioetl-records-processed-total, stage)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "type": "query"
      }
    ]
  }
}
```

**Использовать в query:**

```
Query:
sum(bioetl-records-processed-total{stage=~"$stage"})

Legend:
{{stage}}
```

---

## Экспортировать/Импортировать дашборды

### Экспортировать дашборд в JSON

```bash
# Способ 1: Через Grafana UI
# Dashboard → Dashboard settings (⚙️)
# → JSON Model
# → Copy to clipboard
# → Сохранить в файл

# Способ 2: Через API
curl http://localhost:3000/api/dashboards/uid/bioetl-simple \
  -H "Authorization: Bearer YOUR-API-TOKEN" > bioetl-simple.json
```

### Импортировать дашборд

```bash
# Способ 1: Через UI
# Home → Dashboards → Import
# Загрузить JSON файл или paste JSON

# Способ 2: Через API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR-API-TOKEN" \
  -d @bioetl-simple.json
```

### Автоматическое provisioning

**Скопировать дашборд в provisioning папку:**

```bash
cp bioetl-simple.json ./grafana/dashboards/

# Обновить grafana/provisioning/dashboards/bioetl.yaml:
apiVersion: 1

providers:
  - name: 'BioETL Dashboards'
    orgId: 1
    folder: 'BioETL'
    folderUid: 'bioetl'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards

# Перезапустить Grafana
docker restart bioetl-grafana

# Дашборды автоматически загрузятся!
```

---

## Продвинутые примеры

### Пример 1: Дашборд "Health Check"

```json
{
  "title": "Pipeline Health Check",
  "panels": [
    {
      "title": "System Status",
      "targets": [
        {
          "expr": "up{job=\"bioetl\"}"
        }
      ],
      "type": "stat",
      "options": {
        "colorMode": "background",
        "graphMode": "none"
      }
    },
    {
      "title": "Error Rate Trend",
      "targets": [
        {
          "expr": "avg(bioetl-error-rate) over time"
        }
      ],
      "type": "timeseries"
    },
    {
      "title": "Processing Latency",
      "targets": [
        {
          "expr": "histogram-quantile(0.95, rate(bioetl-processing-duration-seconds-bucket[5m]))"
        }
      ],
      "type": "timeseries"
    }
  ]
}
```

### Пример 2: Динамический дашборд с переменными

```json
{
  "title": "Pipeline Analysis - $pipeline",
  "templating": {
    "list": [
      {
        "name": "pipeline",
        "type": "query",
        "datasource": "Prometheus",
        "definition": "label-values(bioetl-records-processed-total, pipeline)",
        "includeAll": false
      }
    ]
  },
  "panels": [
    {
      "title": "$pipeline - Records Processed",
      "targets": [
        {
          "expr": "sum(bioetl-records-processed-total{pipeline=\"$pipeline\"}) by (stage)"
        }
      ]
    }
  ]
}
```

### Пример 3: Интеграция с внешними уведомлениями

**Настроить Slack webhook:**

```yaml
# В Prometheus alerts.yml
groups:
  - name: slack-alerts
    rules:
      - alert: PipelineDown
        expr: up{job="bioetl"} == 0
        for: 1m
        annotations:
          slack-channel: "#alerts"
          slack-message: "🚨 BioETL Pipeline DOWN!"
```

**Или через Grafana Slack integration:**

```
1. Grafana → Alerting → Notification channels
2. New channel → Slack
3. Webhook URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
4. Test → Save
```

---

## Шпаргалка по PromQL

```promql
# Базовые операции
bioetl-records-processed-total                    # Все значения метрики
bioetl-records-processed-total{stage="bronze"}    # С фильтром
bioetl-records-processed-total{stage=~".*"}       # Regex фильтр
bioetl-records-processed-total offset 1h           # 1 час назад

# Агрегация
sum(bioetl-records-processed-total)               # Сумма всех
avg(bioetl-records-processed-total)               # Среднее
max(bioetl-records-processed-total)               # Максимум

# По меткам
sum(bioetl-records-processed-total) by (stage)    # Группировка
topk(3, bioetl-error-rate)                        # Top 3

# Функции
rate(metric[5m])                                   # Скорость за 5 минут
increase(metric[1h])                               # Прирост за час
histogram-quantile(0.95, metric)                   # 95 перцентиль
time() - metric-timestamp                         # Время жизни

# Логические операции
metric1 + metric2                                  # Сложение
metric1 / metric2                                  # Деление
metric1 > 100                                      # Сравнение
```

---

**Дата:** 22 февраля 2026  
**Версия:** 1.0
