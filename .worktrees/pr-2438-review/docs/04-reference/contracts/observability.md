# Observability Metrics Contract

Этот документ определяет обязательные метрики BioETL для Prometheus.
Все метрики экспортируются через HTTP endpoint на порту 8000 (`/metrics`).

**Версия контракта:** 2.0.0
**Дата:** 2026-02-21
**RFC 2119 Keywords:** MUST, SHOULD, MAY

---

## Соглашения об именовании

Все метрики MUST следовать соглашениям:

| Правило | Пример |
|---------|--------|
| Префикс | `bioetl-` |
| snake-case | `pipeline-duration-seconds` |
| Единицы в суффиксе | `-seconds`, `-total`, `-bytes` |

---

## Pipeline Metrics (MUST)

Эти метрики MUST экспортироваться для каждого запуска пайплайна.

### bioetl-pipeline-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность выполнения этапов пайплайна |
| Labels | `pipeline`, `stage`, `status`, `run-type` |

**Labels:**
- `pipeline`: Имя пайплайна (e.g., `chembl_activity`)
- `stage`: Этап (`fetch`, `transform`, `write-bronze`, `write-silver`, `write-gold`)
- `status`: Результат (`success`, `failure`, `timeout`)
- `run-type`: Тип запуска (`incremental`, `backfill`, `rebuild`)

### bioetl-records-processed-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество обработанных записей |
| Labels | `pipeline`, `stage`, `run-type` |

**Labels:**
- `stage`: Слой данных (`bronze`, `silver`, `gold`, `quarantined`)

### bioetl-errors-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество ошибок |
| Labels | `pipeline`, `stage`, `error-code` |

**Labels:**
- `error-code`: Код ошибки (e.g., `RATE-LIMIT`, `SCHEMA-VIOLATION`, `API-ERROR`)

### bioetl-batch-size-records

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Распределение размеров батчей |
| Labels | `pipeline`, `stage` |
| Buckets | `[100, 500, 1000, 5000, 10000, 50000]` |

---

## Data Quality Metrics (MUST)

### bioetl-dq-records-quarantined-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Записи, отправленные в карантин |
| Labels | `pipeline`, `error-type`, `run-type` |

**Labels:**
- `error-type`: Тип ошибки качества (`invalid-smiles`, `missing-field`, `schema-violation`)

---

## Input Filter Metrics (SHOULD)

### bioetl-filter-ids-loaded-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Уникальные ID загруженные из фильтра |
| Labels | `pipeline`, `source-file` |

### bioetl-filter-ids-duplicates-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Дубликаты ID в источнике фильтра |
| Labels | `pipeline`, `source-file` |

---

## Circuit Breaker Metrics (MUST per ADR-007)

Метрики для мониторинга состояния Circuit Breaker (см. ADR-007).

### bioetl-circuit-breaker-state

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Текущее состояние Circuit Breaker |
| Labels | `adapter` |
| Значения | `0` = closed, `1` = half-open, `2` = open |

### bioetl-circuit-breaker-trips-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Количество срабатываний (transitions to open) |
| Labels | `adapter` |

### bioetl-circuit-breaker-success-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Успешные вызовы через Circuit Breaker |
| Labels | `adapter` |

### bioetl-circuit-breaker-failure-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Неуспешные вызовы через Circuit Breaker |
| Labels | `adapter` |

---

## Storage Metrics (SHOULD)

### bioetl-vacuum-files-removed-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Файлы, удалённые операциями VACUUM |
| Labels | `table`, `layer` |

### bioetl-vacuum-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность операций VACUUM |
| Labels | `table` |

### bioetl-storage-optimization-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Операции оптимизации storage |
| Labels | `pipeline`, `status` |

### bioetl-bronze-write-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность записи в Bronze |
| Labels | `provider`, `entity` |

### bioetl-bronze-records-written-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Записи, записанные в Bronze |
| Labels | `provider`, `entity` |

### bioetl-bronze-bytes-written-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Байты, записанные в Bronze (сжатые) |
| Labels | `provider`, `entity` |

### bioetl-policy-violations-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Нарушения политик записи |
| Labels | `layer`, `mode` |

### bioetl-silver-validation-failures-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Ошибки валидации Silver-схемы |
| Labels | `table` |

---

## Health Check Metrics (MAY)

### bioetl-health_check-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность health check адаптеров |
| Labels | `adapter` |

### bioetl-health_check-status

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Статус health check |
| Labels | `adapter` |
| Значения | `0` = unhealthy, `1` = healthy |

---

## Pipeline Lifecycle Metrics (MUST)

### bioetl-pipeline-runs-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество запусков пайплайна |
| Labels | `pipeline`, `run-type`, `status` |

### bioetl-phase-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность фаз lifecycle (preflight, execution, postrun, cleanup) |
| Labels | `pipeline`, `phase`, `status` |

---

## Transformer Metrics (SHOULD)

### bioetl-transform-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность трансформации данных |
| Labels | `provider`, `entity-type` |

### bioetl-transform-errors-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Ошибки трансформации |
| Labels | `provider`, `entity-type`, `error-type` |

---

## DQ Additional Metrics (SHOULD)

### bioetl-dq-validation-score

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Оценка валидности данных (0.0-1.0) |
| Labels | `pipeline`, `entity` |

### bioetl-dq-soft-threshold-exceeded

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Превышения soft DQ threshold |
| Labels | `pipeline` |

### bioetl-dq-check-duration-ms

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность DQ-проверок (мс) |
| Labels | `pipeline` |

### bioetl-data-freshness-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Timestamp последнего успешного ingestion |
| Labels | `pipeline`, `entity` |

---

## Preflight Metrics (SHOULD)

### bioetl-preflight-medallion-policy-valid

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Валидность medallion policy (1=valid, 0=invalid) |
| Labels | `pipeline`, `run-id` |

### bioetl-preflight-config-errors-total

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Ошибки конфигурации при preflight |
| Labels | `pipeline`, `run-id` |

---

## Adapter / HTTP Metrics (SHOULD)

### bioetl-adapter-request-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность API-запросов адаптера |
| Labels | `provider`, `endpoint` |

### bioetl-adapter-requests-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество API-запросов |
| Labels | `provider`, `endpoint`, `status` |

### bioetl-http-request-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность HTTP-запросов |
| Labels | `provider`, `method`, `status` |

### bioetl-http-retries-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | HTTP retry-попытки |
| Labels | `provider`, `method` |

### bioetl-http-request-errors-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Ошибки HTTP-запросов |
| Labels | `provider`, `method`, `error-type` |

### bioetl-adapter-dropped-duplicates-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Дупликаты, отброшенные адаптером |
| Labels | `provider`, `entity-type` |

### bioetl-data-source-retries-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Retry-попытки data source |
| Labels | `provider`, `operation` |

### bioetl-data-source-retry-exhausted-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Исчерпание retry data source |
| Labels | `provider`, `operation` |

---

## Rate Limiter Metrics (MAY)

### bioetl-rate-limiter-tokens-available

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Доступные токены rate limiter |
| Labels | `provider` |

### bioetl-rate-limiter-wait-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Время ожидания rate limiter |
| Labels | `provider` |

---

## Shutdown Metrics (SHOULD)

### bioetl-shutdown-initiated

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Инициации graceful shutdown |
| Labels | `reason` |

### bioetl-shutdown-completed

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Завершения graceful shutdown |
| Labels | `reason` |

---

## Alerting Thresholds

Рекомендуемые пороги для алертов:

| Метрика | Условие | Severity |
|---------|---------|----------|
| `bioetl-circuit-breaker-state == 2` | > 5 min | Critical |
| `bioetl-errors-total` rate | > 10/min | Warning |
| `bioetl-dq-records-quarantined-total` rate | > 5% of processed | Warning |
| `bioetl-pipeline-duration-seconds` | > 95th percentile + 50% | Warning |

---

## Grafana Dashboard UID

При создании дашбордов использовать UID: `bioetl-pipeline-metrics`

---

## Changelog

### v2.0.0 (2026-02-21)
- Added 30+ new metrics: Pipeline Lifecycle, Transformer, Adapter/HTTP, Rate Limiter, Bronze/Silver, Preflight, Shutdown
- Fixed CB state values: `0.5=half-open` → `1=half-open`, `1=open` → `2=open`
- Fixed vacuum labels: `pipeline, layer` → `table, layer`
- Fixed alerting threshold: `== 1` → `== 2` for open CB state
- Expanded Storage section with Bronze/Silver metrics

### v1.0.0 (2024-12-24)
- Initial contract definition
- Added Circuit Breaker metrics per ADR-007
- Defined MUST/SHOULD/MAY categories
