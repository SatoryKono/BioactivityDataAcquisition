# Observability Metrics Contract

Этот документ определяет обязательные метрики BioETL для Prometheus.
Все метрики экспортируются через HTTP endpoint на порту 8000.

**Версия контракта:** 1.0.1
**Дата:** 2025-12-27
**RFC 2119 Keywords:** MUST, SHOULD, MAY

---

## Соглашения об именовании

Все метрики MUST следовать соглашениям:

| Правило | Пример |
|---------|--------|
| Префикс | `bioetl_` |
| snake_case | `pipeline_duration_seconds` |
| Единицы в суффиксе | `_seconds`, `_total`, `_bytes` |

---

## Pipeline Metrics (MUST)

Эти метрики MUST экспортироваться для каждого запуска пайплайна.

### bioetl_pipeline_duration_seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность выполнения этапов пайплайна |
| Labels | `pipeline`, `stage`, `status`, `run_type` |

**Labels:**
- `pipeline`: Имя пайплайна (e.g., `chembl_activity`)
- `stage`: Этап (`fetch`, `transform`, `write_bronze`, `write_silver`, `write_gold`)
- `status`: Результат (`success`, `failure`, `timeout`)
- `run_type`: Тип запуска (`incremental`, `backfill`, `rebuild`)

### bioetl_records_processed_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество обработанных записей |
| Labels | `pipeline`, `stage`, `run_type` |

**Labels:**
- `stage`: Слой данных (`bronze`, `silver`, `gold`, `quarantined`)

### bioetl_errors_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Общее количество ошибок |
| Labels | `pipeline`, `stage`, `error_code` |

**Labels:**
- `error_code`: Код ошибки (e.g., `RATE_LIMIT`, `SCHEMA_VIOLATION`, `API_ERROR`)

### bioetl_batch_size_records

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Распределение размеров батчей |
| Labels | `pipeline`, `stage` |
| Buckets | `[100, 500, 1000, 5000, 10000, 50000]` |

---

## Data Quality Metrics (MUST)

### bioetl_dq_records_quarantined_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Записи, отправленные в карантин |
| Labels | `pipeline`, `error_type`, `run_type` |

**Labels:**
- `error_type`: Тип ошибки качества (`invalid_smiles`, `missing_field`, `schema_violation`)

---

## Input Filter Metrics (SHOULD)

### bioetl_filter_ids_loaded_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Уникальные ID загруженные из фильтра |
| Labels | `pipeline`, `source_file` |

### bioetl_filter_ids_duplicates_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Дубликаты ID в источнике фильтра |
| Labels | `pipeline`, `source_file` |

---

## Circuit Breaker Metrics (MUST per ADR-007)

Метрики для мониторинга состояния Circuit Breaker (см. ADR-007).

### bioetl_circuit_breaker_state

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Текущее состояние Circuit Breaker |
| Labels | `adapter` |
| Значения | `0` = closed, `0.5` = half-open, `1` = open |

### bioetl_circuit_breaker_trips_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Количество срабатываний (transitions to open) |
| Labels | `adapter` |

### bioetl_circuit_breaker_success_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Успешные вызовы через Circuit Breaker |
| Labels | `adapter` |

### bioetl_circuit_breaker_failure_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Неуспешные вызовы через Circuit Breaker |
| Labels | `adapter` |

---

## Storage Metrics (SHOULD)

### bioetl_storage_write_duration_seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность записи в хранилище |
| Labels | `pipeline`, `layer` |

**Labels:**
- `layer`: `bronze`, `silver`, `gold`

### bioetl_storage_bytes_written_total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Байты записанные в хранилище |
| Labels | `pipeline`, `layer` |

---

## Health Check Metrics (MAY)

### bioetl_health_check_duration_seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность health check адаптеров |
| Labels | `adapter` |

### bioetl_health_check_status

| Свойство | Значение |
|----------|----------|
| Тип | Gauge |
| Описание | Статус health check |
| Labels | `adapter` |
| Значения | `0` = unhealthy, `1` = healthy |

---

## Alerting Thresholds

Рекомендуемые пороги для алертов:

| Метрика | Условие | Severity |
|---------|---------|----------|
| `bioetl_circuit_breaker_state == 1` | > 5 min | Critical |
| `bioetl_errors_total` rate | > 10/min | Warning |
| `bioetl_dq_records_quarantined_total` rate | > 5% of processed | Warning |
| `bioetl_pipeline_duration_seconds` | > 95th percentile + 50% | Warning |

---

## Grafana Dashboard UID

При создании дашбордов использовать UID: `bioetl-pipeline-metrics`

---

## Changelog

### v1.0.0 (2024-12-24)
- Initial contract definition
- Added Circuit Breaker metrics per ADR-007
- Defined MUST/SHOULD/MAY categories
