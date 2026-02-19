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
- `pipeline`: Имя пайплайна (e.g., `chembl-activity`)
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
| Значения | `0` = closed, `0.5` = half-open, `1` = open |

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

### bioetl-storage-write-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность записи в хранилище |
| Labels | `pipeline`, `layer` |

**Labels:**
- `layer`: `bronze`, `silver`, `gold`

### bioetl-storage-bytes-written-total

| Свойство | Значение |
|----------|----------|
| Тип | Counter |
| Описание | Байты записанные в хранилище |
| Labels | `pipeline`, `layer` |

---

## Health Check Metrics (MAY)

### bioetl-health-check-duration-seconds

| Свойство | Значение |
|----------|----------|
| Тип | Histogram |
| Описание | Длительность health check адаптеров |
| Labels | `adapter` |

### bioetl-health-check-status

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
| `bioetl-circuit-breaker-state == 1` | > 5 min | Critical |
| `bioetl-errors-total` rate | > 10/min | Warning |
| `bioetl-dq-records-quarantined-total` rate | > 5% of processed | Warning |
| `bioetl-pipeline-duration-seconds` | > 95th percentile + 50% | Warning |

---

## Grafana Dashboard UID

При создании дашбордов использовать UID: `bioetl-pipeline-metrics`

---

## Changelog

### v1.0.0 (2024-12-24)
- Initial contract definition
- Added Circuit Breaker metrics per ADR-007
- Defined MUST/SHOULD/MAY categories
