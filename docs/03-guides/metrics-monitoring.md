______________________________________________________________________

Version: 6.3.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-05'

______________________________________________________________________

# Metrics & Monitoring Guide

Руководство по настройке и использованию системы метрик и мониторинга в BioETL.

**Версия:** 6.3.0
**Дата обновления:** 2026-04-05

> **Boundary:** this guide focuses on local observability setup, metric
> semantics, and implementation-facing monitoring usage. For shipped operator
> dashboards and alert triage use [Monitoring Guide](../05-operations/01-monitoring-guide.md)
> and [Observability Checklist](../05-operations/runbooks/observability-checklist.md).

______________________________________________________________________

## Обзор

BioETL предоставляет комплексную систему observability:

- **Prometheus Metrics:** Автоматический сбор метрик выполнения
- **Structured Logging:** JSON-логи с correlation ID
- **OpenTelemetry Tracing:** Распределённая трассировка (опционально)
- **Health Checks:** HTTP endpoints для мониторинга состояния

### Canonical operator workflow

Для operator-facing observability discovery используйте один маршрут:

1. `bioetl diagnostics guide` — показать canonical routing по diagnostics surface.
2. `bioetl diagnostics metrics [--json]` — проверить metrics/admin profile:
   текущий metrics endpoint, running/stopped status, tracing/audit flags и
   Pushgateway publication mode.
3. `bioetl diagnostics health [--json]` — проверить provider health.
4. `bioetl diagnostics run --run-id <run-id>` или
   `bioetl diagnostics checkpoint --pipeline <pipeline>` — углубиться в
   run/checkpoint diagnostics.
5. `python -m scripts.engineering.qa report-observability-metric-inventory --json` —
   сверить canonical metric vocabulary между runtime emitters, docs и rules.
6. Сравнить inventory output с
   `grafana/prometheus-rules/bioetl_observability.yml` и shipped Grafana
   dashboard JSON до того, как трактовать missing panel data как runtime outage.

Важно:

- metrics HTTP server startup остаётся auto-managed during normal
  `bioetl run`, `bioetl run-all` и `bioetl run-composite` execution when
  metrics are enabled;
- Pushgateway publication остаётся best-effort on run completion;
- `bioetl diagnostics metrics` — canonical operator summary для этих
  auto-managed behaviors.

#### Observability verification QA

Используйте `report-observability-metric-inventory` как canonical QA surface
для metric drift:

- `direct_live_metrics`: metric families, которые runtime вызывает напрямую
  через canonical metrics API.
- `helper_backed_live_metrics`: metric families, которые проходят через helper
  или wrapper path, но всё ещё реально live.
- `registry_only_metrics`: зарегистрированные metric families без обнаруженного
  runtime emission path.
- `dead_metrics`: строгий поднабор `registry_only_metrics`, для которого в repo
  не осталось ни runtime, ни docs, ни rules evidence.
- `documented_without_runtime` / `ruled_without_runtime`: published operator
  surfaces, которые всё ещё ссылаются на registered family без live runtime
  emission path.

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

______________________________________________________________________

## Конфигурация

### Переменные окружения

| Переменная                              | Описание                       | По умолчанию |
| --------------------------------------- | ------------------------------ | ------------ |
| `BIOETL_OBSERVABILITY__METRICS_ENABLED` | Включить Prometheus метрики    | `true`       |
| `BIOETL_METRICS_PORT`                   | Порт для Prometheus endpoint   | `8000`       |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Включить OpenTelemetry tracing | `false`      |
| `BIOETL_LOG_LEVEL`                      | Уровень логирования            | `INFO`       |

### Включение/отключение

```bash
# Включить метрики (по умолчанию)
export BIOETL_OBSERVABILITY__METRICS_ENABLED=true
export BIOETL_METRICS_PORT=8000

# Tracing остаётся opt-in
export BIOETL_OBSERVABILITY__TRACING_ENABLED=true

# Отключить метрики
export BIOETL_OBSERVABILITY__METRICS_ENABLED=false
```

> **Note:** Prometheus metrics включены по settings default, но OpenTelemetry tracing
> в текущем runtime выключен по умолчанию и активируется только явным
> `BIOETL_OBSERVABILITY__TRACING_ENABLED=true`.
>
> Для short-lived pipeline runs BioETL теперь дополнительно делает best-effort
> публикацию текущего registry в локальный Pushgateway (`localhost:9091` по
> умолчанию). Это снижает риск потери post-run метрик между scrape-циклами
> Prometheus.

______________________________________________________________________

## Prometheus Metrics

### Правила расширения MetricsPort (Implementation MUST)

- **НЕ создавать** новый порт `domain/ports/metrics.py`.
- Расширять существующий контракт `MetricsPort` только в
  `src/bioetl/domain/ports/observability/__init__.py`
  и профильных модулях `src/bioetl/domain/ports/observability/*.py`.
- В текущем проекте используется единый подход: **generic metrics API**.
  Новые метрики добавляются через стандартные методы
  `observe_histogram()` / `increment_counter()` / `set_gauge()` с
  нормализованными строковыми именами.
- Для каждой новой метрики обязательно:
  1. определить объект метрики в
     `src/bioetl/infrastructure/observability/_metrics_defs_*.py`,
  1. зарегистрировать её в `HISTOGRAMS` / `COUNTERS` / `GAUGES` в
     `src/bioetl/infrastructure/observability/prometheus_metrics.py`.

> Если в будущем потребуется typed API, helper-методы добавляются в
> `MetricsPort` во facade `observability/__init__.py` и синхронно
> реализуются в Prometheus и NoOp реализациях без дублирования интерфейсов.

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

| Метрика                            | Тип       | Labels                            | Описание                |
| ---------------------------------- | --------- | --------------------------------- | ----------------------- |
| `bioetl_pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Длительность выполнения |
| `bioetl_records_processed_total`   | Counter   | pipeline, stage, run_type         | Обработанные записи     |
| `bioetl_errors_total`              | Counter   | pipeline, stage, error_code       | Количество ошибок       |
| `bioetl_batch_size_records`        | Histogram | pipeline, stage                   | Размер батчей           |
| `bioetl_pipeline_runs_total`       | Counter   | pipeline, run_type, status        | Количество запусков     |

#### Data Quality Metrics

| Метрика                               | Тип       | Labels                                   | Описание                                                                              |
| ------------------------------------- | --------- | ---------------------------------------- | ------------------------------------------------------------------------------------- |
| `bioetl_dq_records_quarantined_total` | Counter   | pipeline, error_type, run_type           | Карантинные записи                                                                    |
| `bioetl_dq_check_duration_ms`         | Histogram | pipeline                                 | Длительность DQ проверок                                                              |
| `bioetl_dq_validation_failures_total` | Counter   | pipeline, stage, severity                | Превышения DQ порогов; `severity` использует bounded vocabulary `soft_fail` / `hard_fail` |
| `bioetl_dq_validation_score`          | Gauge     | pipeline, entity                         | Оценка валидности (0.0-1.0)                                                           |
| `bioetl_dq_anomaly_detected`          | Counter   | pipeline, metric, severity, anomaly_type | Обнаруженные аномалии                                                                 |
| `bioetl_data_freshness_seconds`       | Gauge     | pipeline, entity                         | Unix timestamp последнего successful ingestion; lag вычисляется как `time() - metric` |
| `bioetl_dq_baseline_updated`          | Counter   | pipeline, metric                         | Обновления baseline                                                                   |
| `bioetl_dq_baseline_samples`          | Gauge     | pipeline, metric                         | Семплы в baseline                                                                     |

### Silver filter rejects: operator semantics

- Для high-level operator summary используйте Prometheus/Grafana signal
  `bioetl_records_processed_total{stage="filtered_out"}`.
- Для coarse quarantine family signal используется bounded label metric
  `quarantine_records_total{reason="filtered_out_silver"}`.
- Этот label intentionally coarse и не должен расширяться raw free-text причинами,
  `message`, или неограниченными значениями полей.
- Exact reason analytics по `reason_code`, `rule_type`, `field`, `operator`
  должны идти через quarantine-derived aggregation или CLI, а не через
  Prometheus labels.
- Для operator-grade bounded dashboard summary используется отдельная metric family
  `bioetl_silver_filter_rejections_total{pipeline,run_type,reason_code,rule_type,field}`.
  Эта метрика не использует `message` и нормализует labels к reviewable bounded
  vocabulary; неизвестные значения схлопываются в `other`.
- Record-level drilldown для Silver rejects остаётся задачей quarantine CLI:
  `bioetl quarantine stats --pipeline <name> --silver-filter-only`
  и `bioetl quarantine inspect --pipeline <name> --silver-filter-only`.

#### Circuit Breaker Metrics

| Метрика                                | Тип     | Labels  | Описание                                  |
| -------------------------------------- | ------- | ------- | ----------------------------------------- |
| `bioetl_circuit_breaker_state`         | Gauge   | adapter | Состояние (0=closed, 1=half-open, 2=open) |
| `bioetl_circuit_breaker_trips_total`   | Counter | adapter | Количество срабатываний                   |
| `bioetl_circuit_breaker_success_total` | Counter | adapter | Успешные вызовы                           |
| `bioetl_circuit_breaker_failure_total` | Counter | adapter | Неуспешные вызовы                         |

#### Pipeline Lifecycle Metrics

| Метрика                         | Тип       | Labels                     | Описание                   |
| ------------------------------- | --------- | -------------------------- | -------------------------- |
| `bioetl_pipeline_runs_total`    | Counter   | pipeline, run_type, status | Количество запусков        |
| `bioetl_phase_duration_seconds` | Histogram | pipeline, phase, status    | Длительность фаз lifecycle |

#### Control Plane & Traceability Metrics

| Метрика                                        | Тип     | Labels                                   | Описание                                                                          |
| ---------------------------------------------- | ------- | ---------------------------------------- | --------------------------------------------------------------------------------- |
| `bioetl_control_plane_manifest_writes_total`   | Counter | pipeline, run_type, status               | Попытки записи immutable run manifest                                             |
| `bioetl_control_plane_ledger_appends_total`    | Counter | pipeline, event_type, status             | Попытки append в run ledger                                                       |
| `bioetl_checkpoint_compatibility_events_total` | Counter | pipeline, disposition                    | Исходы compatibility policy при resume                                            |
| `bioetl_checkpoint_save_events_total`          | Counter | pipeline, operation, status              | Исходы checkpoint save paths (`periodic`, `exception`, `shutdown`, `manual`, composite stage transitions) |
| `bioetl_checkpoint_save_duration_seconds`      | Histogram | pipeline, operation, status            | Длительность checkpoint save operations                                           |
| `bioetl_lineage_fragments_emitted_total`       | Counter | pipeline, layer, status                  | Попытки публикации lineage fragments                                              |
| `bioetl_lineage_refs_missing_total`            | Counter | pipeline, layer, ref_type                | Missing upstream lineage references during persistence                            |
| `bioetl_composite_source_selection_total`      | Counter | pipeline, decision_type, selected_source | Low-cardinality composite source-selection decisions during composite persistence |
| `bioetl_control_plane_reads_total`             | Counter | store, operation, status                  | Срез успехов/промахов/провалов manifest/ledger/lineage lookup-путей              |

> Guardrail: для control-plane/traceability метрик нельзя использовать
> `run_id`, `manifest_id`, paths и другие high-cardinality идентификаторы как
> Prometheus labels. Детализация по конкретному запуску выполняется через
> `bioetl run-manifest show ...`, а не через labels.
>
> `selected_source` для `bioetl_composite_source_selection_total` остаётся
> допустимым label, потому что это bounded provider/source vocabulary, а не
> per-run или per-record идентификатор.

Дополнительный контрольный экран `bioetl-control-plane-v1.json` собирает
агрегированные панели по manifest write failures, ledger append failures,
checkpoint compatibility и read failures. Основной операторский alert для
чтений — `BioETLControlPlaneReadFailureRate` — перебрасывает в
`docs/05-operations/runbooks/observability-checklist.md`, если доля провалов
чтений по store/operation превышает 5% за 30 минут.

#### Transformer Metrics

| Метрика                             | Тип       | Labels                            | Описание                   |
| ----------------------------------- | --------- | --------------------------------- | -------------------------- |
| `bioetl_transform_duration_seconds` | Histogram | provider, entity_type             | Длительность трансформации |
| `bioetl_transform_errors_total`     | Counter   | provider, entity_type, error_type | Ошибки трансформации       |

#### Storage Metrics

| Метрика                                   | Тип       | Labels           | Описание                   |
| ----------------------------------------- | --------- | ---------------- | -------------------------- |
| `bioetl_vacuum_files_removed_total`       | Counter   | table, layer     | Удалённые файлы            |
| `bioetl_bronze_write_duration_seconds`    | Histogram | provider, entity | Длительность записи Bronze |
| `bioetl_bronze_records_written_total`     | Counter   | provider, entity | Записи в Bronze            |
| `bioetl_bronze_bytes_written_total`       | Counter   | provider, entity | Байты в Bronze             |
| `bioetl_policy_violations_total`          | Counter   | layer, mode      | Нарушения политик          |
| `bioetl_silver_validation_failures_total` | Counter   | table, pipeline  | Canonical Silver Pandera validation failures; increments on failed Silver schema validation outcome before `SchemaViolationError` |

#### Audit Traceability Metrics

| Метрика                               | Тип       | Labels                    | Описание                                      |
| ------------------------------------- | --------- | ------------------------- | --------------------------------------------- |
| `bioetl_audit_write_events_total`     | Counter   | layer, operation, status  | Outcomes file-backed audit write operations   |
| `bioetl_audit_write_duration_seconds` | Histogram | layer, operation, status  | Latency of audit write operations             |
| `bioetl_audit_query_events_total`     | Counter   | layer_filter, status      | Outcomes audit inspection/query workflows     |
| `bioetl_audit_query_duration_seconds` | Histogram | layer_filter, status      | Latency of audit inspection/query workflows   |

Guardrail:

- audit metrics remain low-cardinality;
- `run_id`, `table_name`, filesystem paths, and record identifiers must not be
  exposed as Prometheus labels for audit families;
- record-level drilldown stays in audit files and CLI inspection paths rather
  than metric labels.

#### Input Filter Metrics

| Метрика                                   | Тип     | Labels                | Описание            |
| ----------------------------------------- | ------- | --------------------- | ------------------- |
| `bioetl_filter_ids_loaded_total`          | Counter | pipeline, source_file | Загруженные ID      |
| `bioetl_filter_ids_duplicates_total`      | Counter | pipeline, source_file | Дубликаты ID        |
| `bioetl_filter_combinations_loaded_total` | Counter | pipeline, source_file | Комбинации фильтров |

#### Health Check Metrics

| Метрика                                | Тип       | Labels              | Описание                                                  |
| -------------------------------------- | --------- | ------------------- | --------------------------------------------------------- |
| `bioetl_health_check_status`           | Gauge     | component           | Статус (0=unknown, 1=healthy, 2=degraded)                 |
| `bioetl_pipeline_health_check_passed`  | Gauge     | pipeline, component | Статус компонента                                         |
| `bioetl_provider_health_status`        | Gauge     | provider            | Статус провайдера                                         |
| `bioetl_health_check_duration_seconds` | Histogram | pipeline            | Длительность health check                                 |
| `bioetl_health_check_latency_seconds`  | Histogram | provider            | Латентность health check                                  |
| `bioetl_health_check_success_total`    | Counter   | provider            | Health checks со статусом `HEALTHY`                       |
| `bioetl_health_check_degraded_total`   | Counter   | provider            | Health checks со статусом `DEGRADED`                      |
| `bioetl_health_check_failures_total`   | Counter   | provider            | Health checks со статусом `UNHEALTHY` или probe-exception |

#### Preflight Metrics

| Метрика                                   | Тип   | Labels   | Описание                        |
| ----------------------------------------- | ----- | -------- | ------------------------------- |
| `bioetl_infrastructure_validated`         | Gauge | pipeline | Статус валидации инфраструктуры |

#### Adapter / HTTP Metrics

| Метрика                                    | Тип       | Labels                       | Описание                   |
| ------------------------------------------ | --------- | ---------------------------- | -------------------------- |
| `bioetl_adapter_request_duration_seconds`  | Histogram | provider, endpoint           | Длительность API-запросов  |
| `bioetl_adapter_requests_total`            | Counter   | provider, endpoint, status   | Количество API-запросов    |
| `bioetl_adapter_batch_size`                | Histogram | provider, endpoint           | Размер ответов             |
| `bioetl_adapter_dropped_duplicates_total`  | Counter   | provider, entity_type        | Дупликаты отброшенные      |
| `bioetl_http_request_duration_seconds`     | Histogram | provider, method, status     | Длительность HTTP-запросов |
| `bioetl_http_retries_total`                | Counter   | provider, method             | HTTP retry-попытки         |
| `bioetl_http_request_errors_total`         | Counter   | provider, method, error_type | Ошибки HTTP                |
| `bioetl_data_source_retries_total`         | Counter   | provider, operation          | Retry data source          |
| `bioetl_data_source_retry_exhausted_total` | Counter   | provider, operation          | Retry исчерпан             |

#### Rate Limiter Metrics

| Метрика                                | Тип       | Labels   | Описание         |
| -------------------------------------- | --------- | -------- | ---------------- |
| `bioetl_rate_limiter_tokens_available` | Gauge     | provider | Доступные токены |
| `bioetl_rate_limiter_wait_seconds`     | Histogram | provider | Время ожидания   |

#### Shutdown Metrics

| Метрика                     | Тип     | Labels | Описание            |
| --------------------------- | ------- | ------ | ------------------- |
| `bioetl_shutdown_initiated` | Counter | reason | Инициация shutdown  |
| `bioetl_shutdown_completed` | Counter | reason | Завершение shutdown |

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

______________________________________________________________________

## Structured Logging

### Log Schema

Все логи следуют единой схеме с обязательными полями:

| Поле       | Обязательно | Описание                                  |
| ---------- | ----------- | ----------------------------------------- |
| `ts`       | MUST        | ISO timestamp                             |
| `level`    | MUST        | Log level (DEBUG, INFO, WARNING, ERROR)   |
| `run-id`   | MUST        | UUID correlation ID                       |
| `pipeline` | MUST        | Имя пайплайна                             |
| `stage`    | SHOULD      | Этап (extract, transform, load, validate) |
| `event`    | MUST        | Описание события                          |

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

| Уровень   | Использование                                   |
| --------- | ----------------------------------------------- |
| `DEBUG`   | Детальная информация для troubleshooting        |
| `INFO`    | Нормальные операции (default)                   |
| `WARNING` | Предупреждения (DQ soft threshold, rate limits) |
| `ERROR`   | Ошибки, требующие внимания                      |

### Настройка уровня

```bash
# Via переменную окружения
export BIOETL_LOG_LEVEL=DEBUG

# Via CLI флаг
bioetl run --pipeline chembl_activity --debug
```

______________________________________________________________________

## OpenTelemetry Tracing

### Включение

```bash
export BIOETL_OBSERVABILITY__TRACING_ENABLED=true
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

| Span                 | Attributes                              |
| -------------------- | --------------------------------------- |
| `pipeline-execution` | pipeline, run_id, entity_type, run_type |
| `batch-{n}`          | batch_id, record_count, start_index     |
| `write-{layer}`      | batch_id, record_count                  |
| `transform`          | silver_count, gold_count                |

### Экспорт трассировки

По умолчанию используется OTLP exporter. Для локальной разработки доступен ConsoleExporter:

```bash
# Production (OTLP)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Local Tempo over plaintext gRPC
export OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
# OTEL_EXPORTER_OTLP_INSECURE=true выставляется автоматически,
# если endpoint указывает на локальный Tempo и override не задан.

# Development (Console)
# Настраивается автоматически при отсутствии OTLP endpoint
```

______________________________________________________________________

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

| Endpoint                | Описание           | Response                     |
| ----------------------- | ------------------ | ---------------------------- |
| `GET /health`           | Общий статус       | `{"status": "healthy"}`      |
| `GET /health/live`      | Liveness probe     | `{"status": "alive"}`        |
| `GET /health/ready`     | Readiness probe    | `{"status": "ready"}`        |
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

______________________________________________________________________

## Alerting

### Рекомендуемые пороги

| Метрика                                    | Условие                                                | Severity |
| ------------------------------------------ | ------------------------------------------------------ | -------- |
| `bioetl_circuit_breaker_state == 2`        | > 5 min                                                | Critical |
| `bioetl_errors_total` rate                 | > 10/min                                               | Warning  |
| `bioetl_dq_records_quarantined_total` rate | > 5% and \<=20% of processed, with >=20 bronze records | Warning  |
| `bioetl_dq_records_quarantined_total` rate | > 20% of processed, with >=20 bronze records           | Critical |
| `bioetl_pipeline_duration_seconds`         | > 95th percentile + 50%                                | Warning  |
| `bioetl_health_check_status == 0`          | > 1 min                                                | Critical |
| `time() - bioetl_data_freshness_seconds`   | > 24h and \<=72h                                       | Warning  |
| `time() - bioetl_data_freshness_seconds`   | > 72h                                                  | Critical |
| `bioetl_data_source_retry_exhausted_total` | 1-2 exhaustions in 1h                                  | Warning  |
| `bioetl_data_source_retry_exhausted_total` | >=3 exhaustions in 1h                                  | Critical |

Smoke baseline для этих границ закреплён в
`tests/integration/test_prometheus_rules_config.py`, чтобы warning/critical окна
не начинали перекрываться при последующих правках rule pack.

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

______________________________________________________________________

## Grafana Dashboard

### Рекомендуемый Dashboard UID

При создании дашбордов используйте: `bioetl_pipeline-metrics`

### Основные панели

1. **Pipeline Overview**

   - Количество запусков по статусу
   - Длительность выполнения (histogram)
   - Обработанные записи (counter)

1. **Data Quality**

   - Карантинные записи
   - DQ validation score
   - Anomaly detection

1. **Circuit Breaker**

   - Состояние по провайдерам
   - Количество срабатываний
   - Success/Failure rate

1. **Performance**

   - Batch size distribution
   - Write duration by layer
   - VACUUM duration

### DQ lifecycle metrics

- `bioetl_dq_context_build_failures_total` tracks failures while building dataframe context for DQ reports.
- `bioetl_dq_report_skipped_total` tracks layer-specific DQ report skips with bounded reasons.
- `bioetl_dq_report_generated_total` tracks successfully generated Bronze/Silver/Gold DQ reports.

Use these counters together with `2. Runtime` when DQ reports appear to be missing:
they let you distinguish between context-build failures, expected skips, and
successful report generation without relying only on warning logs.

### Trace coverage metric

- `bioetl_traced_runs_total` tracks pipeline runs that started with a real tracing implementation.

Use this counter together with `2. Runtime` and Tempo:

- `Trace-enabled Runs (24h) = 0` means empty Tempo is expected for the selected pipeline/run_type window.
- `Trace-enabled Runs (24h) > 0` plus empty Tempo usually means a broken tracing/export path rather than an intentionally untraced run.

### Checkpoint recovery tracing

- `checkpoint_save` spans are emitted by both ordinary and composite checkpoint
  save paths when tracing is enabled.
- Bounded checkpoint tracing attributes are intentionally shared across these
  paths:
  - `bioetl.pipeline`
  - `bioetl.checkpoint.operation`
  - `bioetl.checkpoint.scope`
  - `bioetl.checkpoint.status`
- `bioetl.checkpoint.operation` remains bounded to the published save families
  such as `periodic`, `exception`, `shutdown`, `manual`, and composite stage
  transitions that persist composite checkpoint state.
- Use `checkpoint_save` spans together with
  `bioetl_checkpoint_save_events_total` and
  `bioetl_checkpoint_save_duration_seconds` when debugging resume and graceful
  shutdown behavior.

### Control-plane read metrics

- `bioetl_control_plane_reads_total` tracks manifest, ledger, and lineage lookup outcomes.
- `bioetl_control_plane_read_duration_seconds` tracks latency for the same read/list operations.

Bounded labels are used intentionally:

- `store`: `manifest`, `ledger`, `lineage`
- `operation`: lookup/list operation class such as `get`, `get_by_run_id`, `list_entries`
- `status`: `success`, `miss`, `failed`

Use these metrics to answer a different question than write counters:
did control-plane state fail to persist, or was it persisted successfully but
could not be read back during investigation and follow-up processing?

______________________________________________________________________

## NoOp режим

При отключении observability используются NoOp реализации:

| Компонент   | NoOp реализация                  |
| ----------- | -------------------------------- |
| MetricsPort | `NoOpMetrics` — все методы no-op |
| TracingPort | `NoOpTracing` — фиктивный tracer |
| LoggerPort  | `UnifiedLogger` — всегда активен |

> **Note:** Логирование всегда включено. Отключить можно только метрики и трассировку.

______________________________________________________________________

## Troubleshooting

### Метрики не отображаются

1. Проверить что метрики включены:

   ```bash
   echo $BIOETL_OBSERVABILITY__METRICS_ENABLED  # should be "true"
   ```

1. Проверить endpoint:

   ```bash
   curl http://localhost:8000/metrics | head -20
   ```

1. Проверить порт не занят:

   ```bash
   lsof -i :8000
   ```

### Health check падает

1. Проверить connectivity к провайдеру:

   ```bash
   bioetl health check --provider chembl
   ```

1. Проверить логи на ошибки:

   ```bash
   grep -i error logs/bioetl.log
   ```

### Tracing не работает

1. Проверить что tracing включён:

   ```bash
   echo $BIOETL_OBSERVABILITY__TRACING_ENABLED  # should be "true"
   ```

1. Проверить OTLP endpoint:

   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   ```

______________________________________________________________________

## См. также

- [Observability Metrics Contract](../04-reference/contracts/observability.md) — полный каталог метрик
- [Observability Architecture](../02-architecture/observability-layers.md) — архитектура observability
- [Observability Checklist](../05-operations/runbooks/observability-checklist.md) — чек-лист для адаптеров
- [ADR-017: Observability Architecture](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [ADR-019: Observability Port Enforcement](../02-architecture/decisions/ADR-019-observability-port-enforcement.md)
