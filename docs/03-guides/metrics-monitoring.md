# Metrics & Monitoring Guide

Руководство по настройке и использованию системы метрик и мониторинга в BioETL.

**Версия:** 5.9.0
**Дата обновления:** 2026-01-26

---

## Обзор

BioETL предоставляет комплексную систему observability:

- **Prometheus Metrics:** Автоматический сбор метрик выполнения
- **Structured Logging:** JSON-логи с correlation ID
- **OpenTelemetry Tracing:** Распределённая трассировка (опционально)
- **Health Checks:** HTTP endpoints для мониторинга состояния

### Архитектура Observability

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Application    │    │  Infrastructure  │    │    External      │
│   (Pipeline)     │    │   (Adapters)     │    │   (Prometheus)   │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ PipelineObserver │───▶│ PrometheusMetrics│───▶│ :8000/metrics    │
│ BatchMetrics     │    │ UnifiedLogger    │    │ Grafana          │
│ DQ Service       │    │ OpenTelemetry    │    │ AlertManager     │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BIOETL-METRICS-ENABLED` | Включить Prometheus метрики | `true` |
| `BIOETL-METRICS-PORT` | Порт для Prometheus endpoint | `8000` |
| `BIOETL-TRACING-ENABLED` | Включить OpenTelemetry tracing | `false` |
| `BIOETL-LOG-LEVEL` | Уровень логирования | `INFO` |
| `BIOETL-LOG-FORMAT` | Формат логов (json/text) | `json` |

### Включение/отключение

```bash
# Включить метрики (по умолчанию)
export BIOETL-METRICS-ENABLED=true
export BIOETL-METRICS-PORT=8000

# Включить tracing
export BIOETL-TRACING-ENABLED=true

# Отключить метрики
export BIOETL-METRICS-ENABLED=false
```

---

## Prometheus Metrics

### Доступ к метрикам

После запуска пайплайна метрики доступны на HTTP endpoint:

```bash
# Запуск пайплайна
bioetl run --pipeline chembl-activity

# В другом терминале
curl http://localhost:8000/metrics | grep bioetl-
```

### Каталог метрик

#### Pipeline Metrics (MUST)

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-pipeline-duration-seconds` | Histogram | pipeline, stage, status, run-type | Длительность выполнения |
| `bioetl-records-processed-total` | Counter | pipeline, stage, run-type | Обработанные записи |
| `bioetl-errors-total` | Counter | pipeline, stage, error-code | Количество ошибок |
| `bioetl-batch-size-records` | Histogram | pipeline, stage | Размер батчей |
| `bioetl-pipeline-runs-total` | Counter | pipeline, run-type, status | Количество запусков |

#### Data Quality Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-dq-records-quarantined-total` | Counter | pipeline, error-type, run-type | Карантинные записи |
| `bioetl-dq-check-duration-ms` | Histogram | pipeline | Длительность DQ проверок |
| `bioetl-dq-soft-threshold-exceeded` | Counter | pipeline | Превышения soft threshold |
| `bioetl-dq-validation-score` | Gauge | pipeline, column, check | Оценка валидности |
| `bioetl-dq-anomaly-detected` | Counter | pipeline, metric, severity | Обнаруженные аномалии |

#### Circuit Breaker Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-circuit-breaker-state` | Gauge | adapter | Состояние (0=closed, 1=half-open, 2=open) |
| `bioetl-circuit-breaker-trips-total` | Counter | adapter | Количество срабатываний |
| `bioetl-circuit-breaker-success-total` | Counter | adapter | Успешные вызовы |
| `bioetl-circuit-breaker-failure-total` | Counter | adapter | Неуспешные вызовы |

#### Storage Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-storage-write-duration-seconds` | Histogram | pipeline, layer | Длительность записи |
| `bioetl-vacuum-duration-seconds` | Histogram | pipeline, layer | Длительность VACUUM |
| `bioetl-vacuum-files-removed-total` | Counter | pipeline, layer | Удалённые файлы |
| `bioetl-storage-optimization-total` | Counter | pipeline, status | Оптимизации storage |

#### Input Filter Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-filter-ids-loaded-total` | Counter | pipeline, source-file | Загруженные ID |
| `bioetl-filter-ids-duplicates-total` | Counter | pipeline, source-file | Дубликаты ID |

#### Health Check Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl-health-check-status` | Gauge | adapter | Статус (0=unhealthy, 1=healthy) |
| `bioetl-pipeline-health-check-passed` | Gauge | pipeline, component | Статус компонента |
| `bioetl-provider-health-status` | Gauge | provider | Статус провайдера |

### Примеры PromQL запросов

```promql
# Rate обработки записей за 5 минут
rate(bioetl-records-processed-total{pipeline="chembl-activity"}[5m])

# 95-й перцентиль длительности пайплайна
histogram-quantile(0.95, rate(bioetl-pipeline-duration-seconds-bucket[5m]))

# Количество ошибок за час
increase(bioetl-errors-total[1h])

# Текущее состояние Circuit Breaker
bioetl-circuit-breaker-state{adapter="chembl"}

# Процент карантинных записей
sum(rate(bioetl-dq-records-quarantined-total[5m])) /
sum(rate(bioetl-records-processed-total[5m])) * 100
```

---

## Structured Logging

### Log Schema

Все логи следуют единой схеме с обязательными полями:

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `ts` | MUST | ISO timestamp |
| `level` | MUST | Log level (DEBUG, INFO, WARNING, ERROR) |
| `run-id` | MUST | UUID correlation ID |
| `pipeline` | MUST | Имя пайплайна |
| `stage` | SHOULD | Этап (extract, transform, load, validate) |
| `event` | MUST | Описание события |

### Пример лога

```json
{
  "ts": "2026-01-26T10:30:45.123456Z",
  "level": "INFO",
  "run-id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline": "chembl-activity",
  "stage": "extract",
  "event": "Fetching records",
  "offset": 0,
  "limit": 100,
  "batch-size": 100
}
```

### Уровни логирования

| Уровень | Использование |
|---------|---------------|
| `DEBUG` | Детальная информация для troubleshooting |
| `INFO` | Нормальные операции (default) |
| `WARNING` | Предупреждения (DQ soft threshold, rate limits) |
| `ERROR` | Ошибки, требующие внимания |

### Настройка уровня

```bash
# Via переменную окружения
export BIOETL-LOG-LEVEL=DEBUG

# Via CLI флаг
bioetl run --pipeline chembl-activity --debug
```

---

## OpenTelemetry Tracing

### Включение

```bash
export BIOETL-TRACING-ENABLED=true
```

### Span Hierarchy

```
pipeline-execution
├── batch-0
│   ├── fetch-records
│   ├── transform
│   ├── write-bronze
│   ├── write-silver
│   └── write-gold
├── batch-1
│   └── ...
└── finalize
    ├── vacuum
    └── checkpoint
```

### Span Attributes

| Span | Attributes |
|------|------------|
| `pipeline-execution` | pipeline, run-id, entity-type, run-type |
| `batch-{n}` | batch-id, record-count, start-index |
| `write-{layer}` | batch-id, record-count |
| `transform` | silver-count, gold-count |

### Экспорт трассировки

По умолчанию используется OTLP exporter. Для локальной разработки доступен ConsoleExporter:

```bash
# Production (OTLP)
export OTEL-EXPORTER-OTLP-ENDPOINT=http://jaeger:4317

# Development (Console)
# Настраивается автоматически при отсутствии OTLP endpoint
```

---

## Health Checks

### Health Server

При выполнении пайплайна автоматически запускается HTTP health server:

```bash
# По умолчанию на порту 8080
bioetl run --pipeline chembl-activity

# Кастомный порт
bioetl run --pipeline chembl-activity --health-port 9090

# Отключить
bioetl run --pipeline chembl-activity --no-health-server
```

### Endpoints

| Endpoint | Описание | Response |
|----------|----------|----------|
| `GET /health` | Общий статус | `{"status": "healthy"}` |
| `GET /health/live` | Liveness probe | `{"status": "alive"}` |
| `GET /health/ready` | Readiness probe | `{"status": "ready"}` |
| `GET /health/providers` | Статус провайдеров | `{"chembl": "healthy", ...}` |

### Standalone Health Server

Для отдельного мониторинга без запуска пайплайна:

```bash
bioetl health server --host 0.0.0.0 --port 8080
```

### CLI Health Check

```bash
# Проверить все провайдеры
bioetl health check

# Проверить конкретные провайдеры
bioetl health check --provider chembl --provider pubchem

# JSON output
bioetl health check --json
```

---

## Alerting

### Рекомендуемые пороги

| Метрика | Условие | Severity |
|---------|---------|----------|
| `bioetl-circuit-breaker-state == 2` | > 5 min | Critical |
| `bioetl-errors-total` rate | > 10/min | Warning |
| `bioetl-dq-records-quarantined-total` rate | > 5% of processed | Warning |
| `bioetl-pipeline-duration-seconds` | > 95th percentile + 50% | Warning |
| `bioetl-health-check-status == 0` | > 1 min | Critical |

### Пример Alertmanager правил

```yaml
groups:
  - name: bioetl
    rules:
      - alert: CircuitBreakerOpen
        expr: bioetl-circuit-breaker-state == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.adapter }}"

      - alert: HighErrorRate
        expr: rate(bioetl-errors-total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate for {{ $labels.pipeline }}"

      - alert: HighQuarantineRate
        expr: |
          sum(rate(bioetl-dq-records-quarantined-total[5m])) by (pipeline) /
          sum(rate(bioetl-records-processed-total[5m])) by (pipeline) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High quarantine rate for {{ $labels.pipeline }}"
```

---

## Grafana Dashboard

### Рекомендуемый Dashboard UID

При создании дашбордов используйте: `bioetl-pipeline-metrics`

### Основные панели

1. **Pipeline Overview**
   - Количество запусков по статусу
   - Длительность выполнения (histogram)
   - Обработанные записи (counter)

2. **Data Quality**
   - Карантинные записи
   - DQ validation score
   - Anomaly detection

3. **Circuit Breaker**
   - Состояние по провайдерам
   - Количество срабатываний
   - Success/Failure rate

4. **Performance**
   - Batch size distribution
   - Write duration by layer
   - VACUUM duration

---

## NoOp режим

При отключении observability используются NoOp реализации:

| Компонент | NoOp реализация |
|-----------|-----------------|
| MetricsPort | `NoOpMetrics` — все методы no-op |
| TracingPort | `NoOpTracing` — фиктивный tracer |
| LoggerPort | `UnifiedLogger` — всегда активен |

> **Note:** Логирование всегда включено. Отключить можно только метрики и трассировку.

---

## Troubleshooting

### Метрики не отображаются

1. Проверить что метрики включены:
   ```bash
   echo $BIOETL-METRICS-ENABLED  # should be "true"
   ```

2. Проверить endpoint:
   ```bash
   curl http://localhost:8000/metrics | head -20
   ```

3. Проверить порт не занят:
   ```bash
   lsof -i :8000
   ```

### Health check падает

1. Проверить connectivity к провайдеру:
   ```bash
   bioetl health check --provider chembl
   ```

2. Проверить логи на ошибки:
   ```bash
   grep -i error logs/bioetl.log
   ```

### Tracing не работает

1. Проверить что tracing включён:
   ```bash
   echo $BIOETL-TRACING-ENABLED  # should be "true"
   ```

2. Проверить OTLP endpoint:
   ```bash
   echo $OTEL-EXPORTER-OTLP-ENDPOINT
   ```

---

## См. также

- [Observability Metrics Contract](../04-reference/contracts/observability.md) — полный каталог метрик
- [Observability Architecture](../02-architecture/observability-layers.md) — архитектура observability
- [Observability Checklist](../05-operations/runbooks/observability-checklist.md) — чек-лист для адаптеров
- [ADR-017: Observability Architecture](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [ADR-019: Observability Port Enforcement](../02-architecture/decisions/ADR-019-observability-port-enforcement.md)
