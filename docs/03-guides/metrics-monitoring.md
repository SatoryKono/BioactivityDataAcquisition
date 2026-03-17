# Metrics & Monitoring Guide

Руководство по настройке и использованию системы метрик и мониторинга в BioETL.

**Версия:** 6.0.0
**Дата обновления:** 2026-02-21

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
| `BIOETL_LOG_LEVEL` | Уровень логирования | `INFO` |

### Включение/отключение

```bash
# Включить метрики (по умолчанию)
export BIOETL_METRICS_ENABLED=true
export BIOETL_METRICS_PORT=8000

# Отключить метрики
export BIOETL_METRICS_ENABLED=false
```

---

## Prometheus Metrics

### Правила расширения MetricsPort (Implementation MUST)

- **НЕ создавать** новый порт `domain/ports/metrics.py`.
- Расширять существующий контракт `MetricsPort` только в
  `src/bioetl/domain/ports/observability.py`.
- В текущем проекте используется единый подход: **generic metrics API**.
  Новые метрики добавляются через стандартные методы
  `observe-histogram()` / `increment-counter()` / `set-gauge()` с
  нормализованными строковыми именами.
- Для каждой новой метрики обязательно:
  1. определить объект метрики в
     `src/bioetl/infrastructure/observability/metrics.py`,
  2. зарегистрировать её в `HISTOGRAMS` / `COUNTERS` / `GAUGES` в
     `src/bioetl/infrastructure/observability/prometheus_metrics.py`.

> Если в будущем потребуется typed API, helper-методы добавляются в
> `MetricsPort` в `observability.py` и синхронно реализуются в Prometheus и
> NoOp реализациях без дублирования интерфейсов.

### Доступ к метрикам

После запуска пайплайна метрики доступны на HTTP endpoint:

```bash
# Запуск пайплайна
bioetl run --pipeline chembl_activity

# В другом терминале
curl http://localhost:8000/metrics | grep bioetl_
```

> Примечание: в Prometheus имена метрик в BioETL используют snake_case
> (`bioetl_*`), а не kebab-case.

### Каталог метрик

#### Pipeline Metrics (MUST)

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_pipeline-duration-seconds` | Histogram | pipeline, stage, status, run-type | Длительность выполнения |
| `bioetl_records-processed-total` | Counter | pipeline, stage, run-type | Обработанные записи |
| `bioetl_errors-total` | Counter | pipeline, stage, error-code | Количество ошибок |
| `bioetl_batch-size-records` | Histogram | pipeline, stage | Размер батчей |
| `bioetl_pipeline-runs-total` | Counter | pipeline, run-type, status | Количество запусков |

#### Data Quality Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_dq-records-quarantined-total` | Counter | pipeline, error-type, run-type | Карантинные записи |
| `bioetl_dq-check-duration-ms` | Histogram | pipeline | Длительность DQ проверок |
| `bioetl_dq-soft-threshold-exceeded` | Counter | pipeline | Превышения soft threshold |
| `bioetl_dq-validation-score` | Gauge | pipeline, entity | Оценка валидности (0.0-1.0) |
| `bioetl_dq-anomaly-detected` | Counter | pipeline, metric, severity, anomaly-type | Обнаруженные аномалии |
| `bioetl_data-freshness-seconds` | Gauge | pipeline, entity | Timestamp последнего ingestion |
| `bioetl_dq-baseline-updated` | Counter | pipeline, metric | Обновления baseline |
| `bioetl_dq-baseline-samples` | Gauge | pipeline, metric | Семплы в baseline |

#### Circuit Breaker Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_circuit-breaker-state` | Gauge | adapter | Состояние (0=closed, 1=half-open, 2=open) |
| `bioetl_circuit-breaker-trips-total` | Counter | adapter | Количество срабатываний |
| `bioetl_circuit-breaker-success-total` | Counter | adapter | Успешные вызовы |
| `bioetl_circuit-breaker-failure-total` | Counter | adapter | Неуспешные вызовы |

#### Pipeline Lifecycle Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_pipeline-runs-total` | Counter | pipeline, run-type, status | Количество запусков |
| `bioetl_phase-duration-seconds` | Histogram | pipeline, phase, status | Длительность фаз lifecycle |

#### Transformer Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_transform-duration-seconds` | Histogram | provider, entity-type | Длительность трансформации |
| `bioetl_transform-errors-total` | Counter | provider, entity-type, error-type | Ошибки трансформации |

#### Storage Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_vacuum-duration-seconds` | Histogram | table | Длительность VACUUM |
| `bioetl_vacuum-files-removed-total` | Counter | table, layer | Удалённые файлы |
| `bioetl_storage-optimization-total` | Counter | pipeline, status | Оптимизации storage |
| `bioetl_bronze-write-duration-seconds` | Histogram | provider, entity | Длительность записи Bronze |
| `bioetl_bronze-records-written-total` | Counter | provider, entity | Записи в Bronze |
| `bioetl_bronze-bytes-written-total` | Counter | provider, entity | Байты в Bronze |
| `bioetl_policy-violations-total` | Counter | layer, mode | Нарушения политик |
| `bioetl_silver-validation-failures-total` | Counter | table | Ошибки валидации Silver |

#### Input Filter Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_filter-ids-loaded-total` | Counter | pipeline, source-file | Загруженные ID |
| `bioetl_filter-ids-duplicates-total` | Counter | pipeline, source-file | Дубликаты ID |
| `bioetl_filter-combinations-loaded-total` | Counter | pipeline, source-file | Комбинации фильтров |

#### Health Check Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_health_check-status` | Gauge | component | Статус (0=unknown, 1=healthy, 2=degraded) |
| `bioetl_pipeline-health_check-passed` | Gauge | pipeline, component | Статус компонента |
| `bioetl_provider-health-status` | Gauge | provider | Статус провайдера |
| `bioetl_health_check-duration-seconds` | Histogram | pipeline | Длительность health check |
| `bioetl_health_check-latency-seconds` | Histogram | provider | Латентность health check |
| `bioetl_health_check-success-total` | Counter | provider | Успешные health checks |
| `bioetl_health_check-failures-total` | Counter | provider | Неуспешные health checks |

#### Preflight Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_preflight-medallion-policy-valid` | Gauge | pipeline, run-id | Валидность medallion policy |
| `bioetl_preflight-config-errors-total` | Gauge | pipeline, run-id | Ошибки конфигурации |
| `bioetl_infrastructure-validated` | Gauge | pipeline, run-id | Статус валидации инфраструктуры |

#### Adapter / HTTP Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_adapter-request-duration-seconds` | Histogram | provider, endpoint | Длительность API-запросов |
| `bioetl_adapter-requests-total` | Counter | provider, endpoint, status | Количество API-запросов |
| `bioetl_adapter-batch-size` | Histogram | provider, endpoint | Размер ответов |
| `bioetl_adapter-dropped-duplicates-total` | Counter | provider, entity-type | Дупликаты отброшенные |
| `bioetl_http-request-duration-seconds` | Histogram | provider, method, status | Длительность HTTP-запросов |
| `bioetl_http-retries-total` | Counter | provider, method | HTTP retry-попытки |
| `bioetl_http-request-errors-total` | Counter | provider, method, error-type | Ошибки HTTP |
| `bioetl_data-source-retries-total` | Counter | provider, operation | Retry data source |
| `bioetl_data-source-retry-exhausted-total` | Counter | provider, operation | Retry исчерпан |

#### Rate Limiter Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_rate-limiter-tokens-available` | Gauge | provider | Доступные токены |
| `bioetl_rate-limiter-wait-seconds` | Histogram | provider | Время ожидания |

#### Shutdown Metrics

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `bioetl_shutdown-initiated` | Counter | reason | Инициация shutdown |
| `bioetl_shutdown-completed` | Counter | reason | Завершение shutdown |

### Примеры PromQL запросов

```promql
# Rate обработки записей за 5 минут
rate(bioetl_records-processed-total{pipeline="chembl_activity"}[5m])

# 95-й перцентиль длительности пайплайна
histogram-quantile(0.95, rate(bioetl_pipeline-duration-seconds-bucket[5m]))

# Количество ошибок за час
increase(bioetl_errors-total[1h])

# Текущее состояние Circuit Breaker
bioetl_circuit-breaker-state{adapter="chembl"}

# Процент карантинных записей
sum(rate(bioetl_dq-records-quarantined-total[5m])) /
sum(rate(bioetl_records-processed-total[5m])) * 100
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
  "pipeline": "chembl_activity",
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
# По умолчанию на порту 8081
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
bioetl health server --host 0.0.0.0 --port 8081
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
| `bioetl_circuit-breaker-state == 2` | > 5 min | Critical |
| `bioetl_errors-total` rate | > 10/min | Warning |
| `bioetl_dq-records-quarantined-total` rate | > 5% of processed | Warning |
| `bioetl_pipeline-duration-seconds` | > 95th percentile + 50% | Warning |
| `bioetl_health_check-status == 0` | > 1 min | Critical |

### Пример Alertmanager правил

```yaml
groups:
  - name: bioetl
    rules:
      - alert: CircuitBreakerOpen
        expr: bioetl_circuit-breaker-state == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.adapter }}"

      - alert: HighErrorRate
        expr: rate(bioetl_errors-total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate for {{ $labels.pipeline }}"

      - alert: HighQuarantineRate
        expr: |
          sum(rate(bioetl_dq-records-quarantined-total[5m])) by (pipeline) /
          sum(rate(bioetl_records-processed-total[5m])) by (pipeline) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High quarantine rate for {{ $labels.pipeline }}"
```

---

## Grafana Dashboard

### Рекомендуемый Dashboard UID

При создании дашбордов используйте: `bioetl_pipeline-metrics`

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
   echo $OTEL-EXPORTER-OTLP-ENDPOINT
   ```

---

## См. также

- [Observability Metrics Contract](../04-reference/contracts/observability.md) — полный каталог метрик
- [Observability Architecture](../02-architecture/observability-layers.md) — архитектура observability
- [Observability Checklist](../05-operations/runbooks/observability-checklist.md) — чек-лист для адаптеров
- [ADR-017: Observability Architecture](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [ADR-019: Observability Port Enforcement](../02-architecture/decisions/ADR-019-observability-port-enforcement.md)
