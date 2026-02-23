# Grafana Dashboard Audit & Consolidated Refactoring Plan

*Date: 2026-02-23 | Scope: grafana/, metrics, observability*

---

## Part I: Audit Findings

### Inventory

| Artifact | Path | Description |
|----------|------|-------------|
| **Dashboards (4)** | `grafana/dashboards/*.json` | simple, overview-v2, dq-v2, provider-health-v2 |
| **Metric definitions** | `src/bioetl/infrastructure/observability/metrics.py` | 52 metrics (Histogram, Counter, Gauge) |
| **Prometheus adapter** | `src/bioetl/infrastructure/observability/prometheus_metrics.py` | PrometheusMetrics implements MetricsPort |
| **Metrics server** | `src/bioetl/infrastructure/observability/server.py` | HTTP exposition + Pushgateway push |
| **Demo server** | `docs/03-guides/dashbords/metrics_server.py` | Synthetic metrics for testing |
| **Fix script** | `scripts/fix_grafana_dashboards.py` | Variable injection into PromQL |
| **Provisioning** | `grafana/provisioning/` | datasources + dashboards auto-load |
| **Docker Compose** | `docker-compose.monitoring.yml` | Prometheus + Pushgateway + Grafana |
| **Tests** | `tests/integration/test_grafana_config.py` | JSON validation, metric contract, required vars |
| **Documentation (16 files)** | `docs/03-guides/dashbords/` | ~145KB total |

### CRITICAL Issues

| ID | Issue | Affected |
|----|-------|----------|
| C-1 | Duplicate `run_id` variable (defined twice in templating.list) | simple, overview-v2, dq-v2 |
| C-2 | Template variables defined but unused in PromQL (`run_id`, `execution` in 3 dashboards; `pipeline`, `run_id` in provider-health) | All 4 dashboards |
| C-3 | DQ dashboard shows zero DQ metrics — only `records_processed_total`. Effectively a clone of Overview | dq-v2 |
| C-4 | ~90% of metrics collected but never visualized (5 out of 52 used) | All dashboards |
| C-5 | Demo metrics server uses different label schema than production (`run_id`+`status` vs `run_type`) and defines non-existent metrics | metrics_server.py |

### HIGH Issues

| ID | Issue | Affected |
|----|-------|----------|
| H-1 | Provider Health shows only health check duration/status. No circuit breaker, HTTP errors, rate limiter, retries | provider-health-v2 |
| H-2 | Fragile `pipeline=~"$provider_.*"` regex assumes `{provider}_{entity}` naming | provider-health-v2 |
| H-3 | Fix script is destructive: overwrites all template variables, not idempotent, no tests | fix_grafana_dashboards.py |
| H-4 | Inconsistent registry keys: some with `bioetl_` prefix, some without | prometheus_metrics.py |
| H-5 | `PrometheusMetrics` silently ignores unknown metric names — hides instrumentation bugs | prometheus_metrics.py |
| H-6 | Datasource referenced by string name `"Prometheus"` instead of UID `{"type":"prometheus","uid":"prometheus"}` | All 4 dashboards |

### MEDIUM Issues

| ID | Issue | Affected |
|----|-------|----------|
| M-1 | `bioetl-simple.json` fully overlaps with overview-v2 (same 5 panels) | simple |
| M-2 | 16 doc files (~145KB) for 4 dashboards; includes changelog-style files | docs/dashbords/ |
| M-3 | Typo in path: `dashbords/` instead of `dashboards/` | docs path |
| M-4 | `schemaVersion: 30` is outdated (Grafana 8.x era) | All dashboards |
| M-5 | `docker-compose.monitoring.yml` uses deprecated `version: '3.8'` | docker-compose |
| M-6 | `host.docker.internal` in prometheus.yml doesn't work on Linux Docker | prometheus.yml |
| M-7 | Corrupted Unicode in dq-v2 panel title (mojibake `в†™` instead of `→`) | dq-v2 |
| M-8 | Division by zero in quality ratio (missing `clamp_min`) | simple, dq-v2 |

### LOW Issues

| ID | Issue |
|----|-------|
| L-1 | `grafana/README.md` is 34K lines — excessive for 4 dashboards |
| L-2 | No alerting rules configured (Grafana or Prometheus) |
| L-3 | `refresh: "5s"` in simple dashboard too aggressive for batch pipeline |
| L-4 | No dashboard links between dashboards for navigation |
| L-5 | Redundant v2/latest-run tags; excessive tag list on simple dashboard |

---

## Part II: Consolidated Refactoring Plan

> Объединяет два независимых плана. Берёт лучшее из каждого:
> - 6-фазная структура альтернативного плана (компактная, actionable)
> - TDD-подход: тесты пишутся рядом с фиксами, а не в конце
> - Конкретные спецификации panels из альтернативного плана
> - Дополнительный scope из моего аудита: demo server, fix script, registry naming, Unicode fix
> - Simple dashboard: оставить как "Operations Glance" (уникальное назначение)

### Phase 1: Critical Bug Fixes + Regression Tests

**Scope:** `grafana/dashboards/*.json`, `tests/integration/test_grafana_config.py`

#### 1.1 Удалить дублирующуюся переменную `run_id`

Файлы: `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json`

В `templating.list` каждого файла `run_id` определён дважды. Удалить второй дубликат.

#### 1.2 Исправить division by zero в quality ratio

Файлы: `bioetl-simple.json`, `bioetl-dq-v2.json`

Заменить:
```
sum(...stage="gold") / sum(...stage="bronze")
```
На (как уже сделано в `bioetl-overview-v2.json`):
```
sum(...stage="gold") / clamp_min(sum(...stage="bronze"), 1)
```

#### 1.3 Удалить неиспользуемую переменную `execution`

Файлы: `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json`

Переменная `execution` запрашивает `bioetl_infrastructure_validated`, но ни один panel её не использует.

#### 1.4 Исправить corrupted Unicode в dq-v2

Файл: `bioetl-dq-v2.json`

Заменить mojibake `"Data Flow: Bronze в†™ Silver в†™ Gold"` на `"Data Flow: Bronze → Silver → Gold"`.

#### 1.5 Добавить тесты для предотвращения регрессий

Файл: `tests/integration/test_grafana_config.py`

Новые тесты:
- `test_no_duplicate_variable_names` — нет дублей в `templating.list`
- `test_all_variables_used_in_panels` — каждая переменная используется хотя бы в одном PromQL query
- `test_quality_ratio_uses_clamp_min` — деление на bronze защищено `clamp_min`

---

### Phase 2: Dashboard Modernization

**Scope:** все 4 dashboard JSON

#### 2.1 Обновить datasource на UID-формат

Все 4 файла (~39 вхождений):
```jsonc
// Было (deprecated в Grafana 10+):
"datasource": "Prometheus"

// Стало:
"datasource": {"type": "prometheus", "uid": "prometheus"}
```

UID `prometheus` совпадает с `grafana/provisioning/datasources/prometheus.yml`.

#### 2.2 Убрать суффикс "v2" из заголовков и тегов

- Заголовки: `"BioETL Data Quality v2"` → `"BioETL Data Quality"` и т.д.
- Теги: удалить `"v2"`, `"latest-run"`; очистить избыточные теги с simple dashboard (`"working"`, `"active"`, `"minimal"`, `"essential"`)
- **НЕ менять UID** (`bioetl-dq-v2` и т.д.) — чтобы не сломать bookmarks

#### 2.3 Обновить `refresh` в simple dashboard

Заменить `"refresh": "5s"` на `"refresh": "30s"` — batch pipeline не требует 5-секундного обновления.

#### 2.4 Добавить dashboard links для навигации

Каждый дашборд получает `"links"` секцию с ссылками на остальные 3 дашборда (по UID).

#### 2.5 Тесты модернизации

Файл: `tests/integration/test_grafana_config.py`

- `test_datasource_uses_uid_format` — все datasource в `{type, uid}` формате
- `test_unique_panel_ids` — уникальность panel id внутри dashboard

---

### Phase 3: Dashboard Enrichment — Новые Panels

**Scope:** все 4 dashboard JSON

Метрики — read-only source of truth: `src/bioetl/infrastructure/observability/metrics.py`

#### 3.1 Data Quality Dashboard (`bioetl-dq-v2.json`) — +8 panels

Оставить существующие panels (Bronze/Gold counts, data flow, timestamp). Добавить:

| Panel | Type | Metric |
|-------|------|--------|
| DQ Validation Score | Gauge | `bioetl_dq_validation_score` |
| Records Quarantined | Stat | `bioetl_dq_records_quarantined_total` |
| Quarantine by Error Type | PieChart | `bioetl_dq_records_quarantined_total` by `error_type` |
| Anomalies Detected | Timeseries | `bioetl_dq_anomaly_detected` |
| DQ Check Duration (p95) | Timeseries | `histogram_quantile(0.95, bioetl_dq_check_duration_ms_bucket)` |
| Soft Threshold Exceeded | Stat | `bioetl_dq_soft_threshold_exceeded` |
| Data Freshness | Gauge | `bioetl_data_freshness_seconds` |
| Silver Validation Failures | Stat | `bioetl_silver_validation_failures_total` |

#### 3.2 Overview Dashboard (`bioetl-overview-v2.json`) — +10 panels

Row **"Pipeline Lifecycle"**:
- Pipeline Duration (p95) — `bioetl_pipeline_duration_seconds` histogram
- Phase Duration Breakdown — `bioetl_phase_duration_seconds` histogram by `phase`
- Pipeline Runs by Status — `bioetl_pipeline_runs_total` by `status`

Row **"Errors"**:
- Total Errors — `bioetl_errors_total` (stat, red threshold)
- Errors by Stage — `bioetl_errors_total` by `(stage, error_code)` (timeseries)

Row **"Transform & Storage"**:
- Transform Duration (p95) — `bioetl_transform_duration_seconds` histogram
- Transform Errors — `bioetl_transform_errors_total`
- Bronze Write Duration — `bioetl_bronze_write_duration_seconds`
- Bronze Records Written — `bioetl_bronze_records_written_total`
- Shutdown Events — `bioetl_shutdown_initiated`

#### 3.3 Provider Health Dashboard (`bioetl-provider-health-v2.json`) — +10 panels

Row **"Circuit Breaker"**:
- CB State (state map) — `bioetl_circuit_breaker_state` (0=closed, 1=half-open, 2=open)
- CB Trips — `bioetl_circuit_breaker_trips_total`
- CB Success vs Failure — stacked bar: `bioetl_circuit_breaker_success_total`, `bioetl_circuit_breaker_failure_total`

Row **"API Performance"**:
- API Request Duration (p95) — `bioetl_adapter_request_duration_seconds` histogram
- API Requests by Status — `bioetl_adapter_requests_total` by `status`

Row **"HTTP Layer"**:
- HTTP Errors — `bioetl_http_request_errors_total` by `error_type`
- HTTP Retries — `bioetl_http_retries_total`

Row **"Rate Limiting"**:
- Rate Limiter Tokens — `bioetl_rate_limiter_tokens_available` gauge
- Rate Limiter Wait Time (p95) — `bioetl_rate_limiter_wait_seconds` histogram
- Provider Health Status (state map) — `bioetl_provider_health_status`

**Также:** заменить fragile `$provider_.*` regex на нормальную template variable из `label_values`.

#### 3.4 Simple Dashboard (`bioetl-simple.json`) — переосмысление как "Operations Glance"

Оставить существующие 5 panels (Bronze/Silver/Gold counts, quality ratio, records timeseries). Добавить:

| Panel | Type | Metric |
|-------|------|--------|
| Errors | Stat (red when > 0) | `bioetl_errors_total` |
| Pipeline Duration | Stat | `bioetl_pipeline_duration_seconds` (latest) |
| Circuit Breaker | Stat (state map) | `bioetl_circuit_breaker_state` |

Итого: 8 panels — минимальный "glance" дашборд для быстрой оценки здоровья, с уникальным назначением отличным от Overview.

#### 3.5 Тесты enrichment

Файл: `tests/integration/test_grafana_config.py`

- `test_metric_coverage_report` — coverage ≥ 50% метрик из `metrics.py`
- `test_promql_balanced_braces` — сбалансированные `{}`, `[]`, `()` в PromQL
- `test_variable_cascade_order` — переменные, зависящие от других, идут после них в list

---

### Phase 4: Supporting Infrastructure

**Scope:** demo server, fix script, prometheus_metrics.py

#### 4.1 Demo metrics server — синхронизация со schema

Файл: `docs/03-guides/dashbords/metrics_server.py`

- Синхронизировать label sets с production-определениями из `metrics.py`
- Удалить несуществующие метрики (`bioetl_processing_duration_seconds`, `bioetl_error_rate`)
- Добавить генерацию DQ, circuit breaker, adapter метрик (хотя бы основных)
- Привести port по умолчанию в соответствие с production (8000)

#### 4.2 Fix script — сделать безопасным

Файл: `scripts/fix_grafana_dashboards.py`

- Заменить перезапись `data["templating"]["list"] = [...]` на **merge** существующих переменных
- Добавить `--dry-run` режим с выводом diff
- Обеспечить идемпотентность (не дублировать фильтры при повторном запуске)

#### 4.3 Registry naming — унификация

Файл: `src/bioetl/infrastructure/observability/prometheus_metrics.py`

- Унифицировать ключи в `HISTOGRAMS`, `COUNTERS`, `GAUGES` — все без `bioetl_` prefix (canonical short name)
- Удалить: `"bioetl_phase_duration_seconds"` → `"phase_duration_seconds"` и т.д.
- Обновить вызывающий код если нужно

#### 4.4 Silent failures — добавить warning

Файл: `src/bioetl/infrastructure/observability/prometheus_metrics.py`

В методах `observe_histogram`, `increment_counter`, `set_gauge` — логировать warning при вызове с неизвестным metric name (вместо silent no-op). Требует инъекции `LoggerPort` или module-level logger.

---

### Phase 5: Documentation & Docker

**Scope:** docs, docker-compose, prometheus.yml, grafana/README.md

#### 5.1 Обновить `grafana/README.md`

- Убрать ссылки на v1 dashboards
- Задокументировать новые panels из Phase 3
- Сократить до разумного размера (текущий: 34K строк)

#### 5.2 Docker и Prometheus

- Удалить deprecated `version: '3.8'` из `docker-compose.monitoring.yml`
- Добавить `extra_hosts: ["host.docker.internal:host-gateway"]` для Linux
- Добавить healthcheck для Prometheus и Grafana сервисов
- Задокументировать `host.docker.internal` ограничение для Linux

#### 5.3 Документация cleanup (optional, P3)

- Консолидировать changelog-style файлы (TIMESTAMP_FIXED.md, INFO_PANELS_ADDED.md, и т.д.) — удалить или объединить в один CHANGELOG
- Целевое количество doc файлов: ≤ 6 (из текущих 16)

---

### Phase 6: Final Verification

#### 6.1 Автоматическая верификация
```bash
# Все integration-тесты зелёные
python -m pytest tests/integration/test_grafana_config.py -v -o "addopts="

# JSON validity
python -c "import json; [json.load(open(f)) for f in __import__('glob').glob('grafana/dashboards/*.json')]"
```

#### 6.2 Ручная верификация
```bash
# Запустить monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Запустить pipeline с реальными метриками
bioetl run chembl_molecule --limit 100

# Проверить в Grafana (http://localhost:3000):
# - Все 4 дашборда загружаются
# - Новые panels показывают данные
# - Template variables работают (фильтрация применяется)
# - Dashboard links навигируют корректно
```

---

## Execution Order & Dependencies

```
Phase 1 (bug fixes + tests)
    │
    ▼
Phase 2 (modernization)
    │
    ▼
Phase 3 (enrichment + tests)
    │               │
    ▼               ▼
Phase 4          Phase 5
(infra)          (docs)
    │               │
    └───────┬───────┘
            ▼
      Phase 6 (verification)
```

Phase 4 и Phase 5 можно выполнять параллельно.

---

## Key Files (read/write)

| File | Access | Phase |
|------|--------|-------|
| `grafana/dashboards/bioetl-simple.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-overview-v2.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-dq-v2.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-provider-health-v2.json` | R/W | 1, 2, 3 |
| `tests/integration/test_grafana_config.py` | R/W | 1, 2, 3 |
| `src/bioetl/infrastructure/observability/metrics.py` | **R/O** | source of truth |
| `src/bioetl/infrastructure/observability/prometheus_metrics.py` | R/W | 4 |
| `docs/03-guides/dashbords/metrics_server.py` | R/W | 4 |
| `scripts/fix_grafana_dashboards.py` | R/W | 4 |
| `grafana/provisioning/datasources/prometheus.yml` | R/O | reference for UID |
| `docker-compose.monitoring.yml` | R/W | 5 |
| `grafana/prometheus.yml` | R/W | 5 |
| `grafana/README.md` | R/W | 5 |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Metrics visualized / defined | ~10% (5/52) | ≥ 60% (31+/52) |
| Dashboards with duplicate vars | 3/4 | 0/4 |
| Unused template variables | ~8 | 0 |
| DQ metrics on DQ dashboard | 0 | 8 |
| Provider metrics on Provider dashboard | 2 | 12 |
| Integration test count (dashboard) | 3 | ≥ 11 |
| Doc files in dashbords/ | 16 | ≤ 6 |
