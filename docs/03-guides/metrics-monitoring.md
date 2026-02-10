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
| `BIOETL_METRICS_ENABLED` | Включить Prometheus метрики | `true` |
| `BIOETL_METRICS_PORT` | Порт для Prometheus endpoint | `8000` |
| `BIOETL_TRACING_ENABLED` | Включить OpenTelemetry tracing | `false` |
| `BIOETL_LOG_LEVEL` | Уровень логирования | `INFO` |
| `BIOETL_LOG_FORMAT` | Формат логов (json/text) | `json` |

### Включение/отключение

```bash
# Включить метрики (по умолчанию)
export BIOETL_METRICS_ENABLED=true
export BIOETL_METRICS_PORT=8000

# Включить tracing
export BIOETL_TRACING_ENABLED=true

# Отключить метрики
export BIOETL_METRICS_ENABLED=false
```

---

## Prometheus Metrics

### Доступ к метрикам

После запуска пайплайна метрики доступны на HTTP endpoint:

```bash
# Запуск пайплайна
bioetl run --pipeline chembl_activity

# В другом терминале
curl http://localhost:8000/metrics | grep bioetl_
```

### Каталог метрик

#### Pipeline Metrics (MUST)

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Длительность выполнения |
| `bioetl_records_processed_total` | Counter | pipeline, stage, run_type | Обработанные записи |
| `bioetl_errors_total` | Counter | pipeline, stage, error_code | Количество ошибок |
| `bioetl_batch_size_records` | Histogram | pipeline, stage | Размер батчей |
| `bioetl_pipeline_runs_total` | Counter | pipeline, run_type, status | Количество запусков |

#### Data Quality Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_dq_records_quarantined_total` | Counter | pipeline, error_type, run_type | Карантинные записи |
| `bioetl_dq_check_duration_ms` | Histogram | pipeline | Длительность DQ проверок |
| `bioetl_dq_soft_threshold_exceeded` | Counter | pipeline | Превышения soft threshold |
| `bioetl_dq_validation_score` | Gauge | pipeline, column, check | Оценка валидности |
| `bioetl_dq_anomaly_detected` | Counter | pipeline, metric, severity | Обнаруженные аномалии |

#### Circuit Breaker Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_circuit_breaker_state` | Gauge | adapter | Состояние (0=closed, 1=half-open, 2=open) |
| `bioetl_circuit_breaker_trips_total` | Counter | adapter | Количество срабатываний |
| `bioetl_circuit_breaker_success_total` | Counter | adapter | Успешные вызовы |
| `bioetl_circuit_breaker_failure_total` | Counter | adapter | Неуспешные вызовы |

#### Storage Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_storage_write_duration_seconds` | Histogram | pipeline, layer | Длительность записи |
| `bioetl_vacuum_duration_seconds` | Histogram | pipeline, layer | Длительность VACUUM |
| `bioetl_vacuum_files_removed_total` | Counter | pipeline, layer | Удалённые файлы |
| `bioetl_storage_optimization_total` | Counter | pipeline, status | Оптимизации storage |

#### Input Filter Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_filter_ids_loaded_total` | Counter | pipeline, source_file | Загруженные ID |
| `bioetl_filter_ids_duplicates_total` | Counter | pipeline, source_file | Дубликаты ID |

#### Health Check Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_health_check_status` | Gauge | adapter | Статус (0=unhealthy, 1=healthy) |
| `bioetl_pipeline_health_check_passed` | Gauge | pipeline, component | Статус компонента |
| `bioetl_provider_health_status` | Gauge | provider | Статус провайдера |

### Примеры PromQL запросов

```promql
# Rate обработки записей за 5 минут
rate(bioetl_records_processed_total{pipeline="chembl_activity"}[5m])

# 95-й перцентиль длительности пайплайна
histogram_quantile(0.95, rate(bioetl_pipeline_duration_seconds_bucket[5m]))

# Количество ошибок за час
increase(bioetl_errors_total[1h])

# Текущее состояние Circuit Breaker
bioetl_circuit_breaker_state{adapter="chembl"}

# Процент карантинных записей
sum(rate(bioetl_dq_records_quarantined_total[5m])) /
sum(rate(bioetl_records_processed_total[5m])) * 100
```

---

## Structured Logging

### Log Schema

Все логи следуют единой схеме с обязательными полями:

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `ts` | MUST | ISO timestamp |
| `level` | MUST | Log level (DEBUG, INFO, WARNING, ERROR) |
| `run_id` | MUST | UUID correlation ID |
| `pipeline` | MUST | Имя пайплайна |
| `stage` | SHOULD | Этап (extract, transform, load, validate) |
| `event` | MUST | Описание события |

### Пример лога

```json
{
  "ts": "2026-01-26T10:30:45.123456Z",
  "level": "INFO",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline": "chembl_activity",
  "stage": "extract",
  "event": "Fetching records",
  "offset": 0,
  "limit": 100,
  "batch_size": 100
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
export BIOETL_LOG_LEVEL=DEBUG

# Via CLI флаг
bioetl run --pipeline chembl_activity --debug
```

---

## OpenTelemetry Tracing

### Включение

```bash
export BIOETL_TRACING_ENABLED=true
```

### Span Hierarchy

```
pipeline_execution
├── batch_0
│   ├── fetch_records
│   ├── transform
│   ├── write_bronze
│   ├── write_silver
│   └── write_gold
├── batch_1
│   └── ...
└── finalize
    ├── vacuum
    └── checkpoint
```

### Span Attributes

| Span | Attributes |
|------|------------|
| `pipeline_execution` | pipeline, run_id, entity_type, run_type |
| `batch_{n}` | batch_id, record_count, start_index |
| `write_{layer}` | batch_id, record_count |
| `transform` | silver_count, gold_count |

### Экспорт трассировки

По умолчанию используется OTLP exporter. Для локальной разработки доступен ConsoleExporter:

```bash
# Production (OTLP)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Development (Console)
# Настраивается автоматически при отсутствии OTLP endpoint
```

---

## Health Checks

### Health Server

При выполнении пайплайна автоматически запускается HTTP health server:

```bash
# По умолчанию на порту 8080
bioetl run --pipeline chembl_activity

# Кастомный порт
bioetl run --pipeline chembl_activity --health-port 9090

# Отключить
bioetl run --pipeline chembl_activity --no-health-server
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
| `bioetl_circuit_breaker_state == 2` | > 5 min | Critical |
| `bioetl_errors_total` rate | > 10/min | Warning |
| `bioetl_dq_records_quarantined_total` rate | > 5% of processed | Warning |
| `bioetl_pipeline_duration_seconds` | > 95th percentile + 50% | Warning |
| `bioetl_health_check_status == 0` | > 1 min | Critical |

### Пример Alertmanager правил

```yaml
groups:
  - name: bioetl
    rules:
      - alert: CircuitBreakerOpen
        expr: bioetl_circuit_breaker_state == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.adapter }}"

      - alert: HighErrorRate
        expr: rate(bioetl_errors_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate for {{ $labels.pipeline }}"

      - alert: HighQuarantineRate
        expr: |
          sum(rate(bioetl_dq_records_quarantined_total[5m])) by (pipeline) /
          sum(rate(bioetl_records_processed_total[5m])) by (pipeline) > 0.05
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
   echo $BIOETL_METRICS_ENABLED  # should be "true"
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
   echo $BIOETL_TRACING_ENABLED  # should be "true"
   ```

2. Проверить OTLP endpoint:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   ```

---

## См. также

- [Observability Metrics Contract](../contracts/observability.md) — полный каталог метрик
- [Observability Architecture](../02-architecture/observability-layers.md) — архитектура observability
- [Observability Checklist](../05-operations/runbooks/observability-checklist.md) — чек-лист для адаптеров
- [ADR-017: Observability Architecture](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [ADR-019: Observability Port Enforcement](../02-architecture/decisions/ADR-019-observability-port-enforcement.md)
