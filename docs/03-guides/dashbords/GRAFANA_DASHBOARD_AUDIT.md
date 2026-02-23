# Grafana Dashboard Audit & Consolidated Refactoring Plan

*Date: 2026-02-23 | Scope: grafana/, metrics, observability, metrics schema*
*Consolidated from 3 independent audit plans*

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
| **DQ Baseline script** | `scripts/dq_baseline_update.py` | Ручной пересчёт baseline из локальных JSON |
| **Fix script** | `scripts/fix_grafana_dashboards.py` | Variable injection into PromQL |
| **Provisioning** | `grafana/provisioning/` | datasources + dashboards auto-load |
| **Docker Compose** | `docker-compose.monitoring.yml` | Prometheus + Pushgateway + Grafana |
| **Tests** | `tests/integration/test_grafana_config.py` | JSON validation, metric contract, required vars |
| **Documentation (16 files)** | `docs/03-guides/dashbords/` | ~145KB total |

### CRITICAL Issues

#### C-1. Root Cause: `run_id` label отсутствует в core-метриках

**Это корневая причина** нескольких видимых багов (дублирование переменных, неработающие фильтры).

Факты:
- `RECORDS_PROCESSED_TOTAL` определён с labels `["pipeline", "stage", "run_type"]` — **без `run_id`**
- Дашборды запрашивают `label_values(bioetl_records_processed_total, run_id)` — возвращает **пустой список**
- Label `run_id` существует только на 3 preflight gauges: `infrastructure_validated`, `preflight_medallion_policy_valid`, `preflight_config_errors_total`
- Результат: dropdown `run_id` во всех дашбордах нефункционален. Пользователи видят фильтр, который ни на что не влияет.

#### C-2. Duplicate `run_id` variable (3 дашборда)

В `templating.list` файлов `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json` переменная `run_id` определена **дважды**. Grafana показывает два dropdown.

#### C-3. Ложная агрегация: "Latest Run Only" не работает

Дашборды заявлены как "Latest Run Only", но PromQL запросы используют `sum(bioetl_records_processed_total{...})`. Counters в Prometheus монотонно растут — `sum()` показывает **накопленную сумму всех запусков**, а не последний. Это "работает" только потому, что Pushgateway (`pushadd_to_gateway`) перезаписывает значения, но при параллельных запусках или смене grouping_key данные суммируются некорректно.

#### C-4. DQ dashboard не показывает DQ-метрики

`bioetl-dq-v2.json` использует только `records_processed_total` и `records_processed_created`. Клон Overview.

Не задействованы: `dq_validation_score`, `dq_records_quarantined_total`, `dq_anomaly_detected`, `dq_baseline_samples`, `dq_check_duration_ms`, `dq_soft_threshold_exceeded`, `dq_baseline_updated`.

#### C-5. Неточная формула качества

Quality Score = `Gold / Bronze`. Это не учитывает:
- Легитимную фильтрацию (дубликаты, filter IDs)
- Карантинированные записи

Корректная формула: `(Gold + Quarantined) / clamp_min(Bronze, 1)` — "закон сохранения записей".

#### C-6. ~90% метрик не визуализируется

5 из 52 метрик используются в дашбордах (~10%). Все circuit breaker, error, DQ, transform, HTTP/adapter, rate limiter, storage метрики игнорируются.

#### C-7. Demo metrics server несовместим с production

`metrics_server.py` определяет labels `['pipeline', 'run_id', 'stage', 'status']` вместо production `['pipeline', 'stage', 'run_type']`. Также определяет несуществующие метрики.

### HIGH Issues

| ID | Issue | Affected |
|----|-------|----------|
| H-1 | Provider Health показывает только health check duration/status. Нет circuit breaker, HTTP errors, rate limiter | provider-health-v2 |
| H-2 | Fragile `pipeline=~"$provider_.*"` regex предполагает формат `{provider}_{entity}` | provider-health-v2 |
| H-3 | Fix script деструктивен: перезаписывает все template variables, не идемпотентен | fix_grafana_dashboards.py |
| H-4 | Inconsistent registry keys: часть с `bioetl_` prefix, часть без | prometheus_metrics.py |
| H-5 | `PrometheusMetrics` молча игнорирует неизвестные metric names — скрывает баги | prometheus_metrics.py |
| H-6 | Datasource по string name `"Prometheus"` вместо UID `{"type":"prometheus","uid":"prometheus"}` | All 4 dashboards |
| H-7 | Ручное управление DQ baseline через `scripts/dq_baseline_update.py` с локальными JSON, в отрыве от Prometheus | dq_baseline_update.py |

### MEDIUM Issues

| ID | Issue | Affected |
|----|-------|----------|
| M-1 | `bioetl-simple.json` fully overlaps with overview-v2 | simple |
| M-2 | 16 doc файлов (~145KB) for 4 dashboards | docs/dashbords/ |
| M-3 | Typo: `dashbords/` вместо `dashboards/` | docs path |
| M-4 | `schemaVersion: 30` устарела (Grafana 8.x) | All dashboards |
| M-5 | `docker-compose.monitoring.yml` deprecated `version: '3.8'` | docker-compose |
| M-6 | `host.docker.internal` не работает на Linux Docker | prometheus.yml |
| M-7 | Corrupted Unicode mojibake в dq-v2 title | dq-v2 |
| M-8 | Division by zero в quality ratio (missing `clamp_min`) | simple, dq-v2 |
| M-9 | Нет reconciliation метрики: расхождение между "отправлено в storage" и "реально записано" | metrics.py |

### LOW Issues

| ID | Issue |
|----|-------|
| L-1 | `grafana/README.md` — 34K строк |
| L-2 | Нет alerting rules |
| L-3 | `refresh: "5s"` в simple — слишком агрессивно для batch pipeline |
| L-4 | Нет dashboard links для навигации |
| L-5 | Избыточные теги (v2, latest-run, working, active, minimal, essential) |

---

## Part II: Consolidated Refactoring Plan

> Объединяет 3 независимых плана:
> 1. **Audit Plan** — обнаружил дублирование, coverage gap, fix script, registry naming
> 2. **Alternative Plan** — компактная 5-фазная структура, конкретные panel specs, TDD-подход
> 3. **Analytics Plan** — root cause `run_id` schema gap, агрегация, DQ формула, baseline automation, observability contract
>
> Структура: 7 фаз. Фазы 1-3 фокусируются на дашбордах (Grafana Layer).
> Фаза 4 решает корневую проблему схемы метрик (Infrastructure Layer).
> Фазы 5-7 — инфраструктура, документация, верификация.

---

### Phase 1: Critical Bug Fixes + Regression Tests

**Priority:** P0
**Scope:** `grafana/dashboards/*.json`, `tests/integration/test_grafana_config.py`

#### 1.1 Удалить дублирующуюся переменную `run_id`

Файлы: `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json`

В `templating.list` каждого файла `run_id` определён дважды. Удалить второй дубликат.

#### 1.2 Исправить переменную `run_id` — переключить на working metric

Во всех 4 дашбордах: заменить источник переменной `run_id` с `bioetl_records_processed_total` (не содержит `run_id` label) на `bioetl_infrastructure_validated` (содержит `run_id` label):

```
// Было (broken — records_processed_total не имеет label run_id):
label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_id)

// Стало (working — infrastructure_validated имеет label run_id):
label_values(bioetl_infrastructure_validated{pipeline=~"$pipeline"}, run_id)
```

#### 1.3 Удалить неиспользуемую переменную `execution`

Файлы: `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json`

Переменная `execution` дублирует `run_id` по смыслу (тоже из `infrastructure_validated`). Удалить.

#### 1.4 Исправить division by zero + формулу Quality Ratio

Файлы: `bioetl-simple.json`, `bioetl-dq-v2.json`

```
// Было (div/0, неточная формула):
sum(...stage="gold") / sum(...stage="bronze")

// Стало (защита от div/0, учёт карантина):
(sum(...stage="gold") + sum(...stage="quarantined"))
  / clamp_min(sum(...stage="bronze"), 1)
```

> **Примечание:** `stage="quarantined"` уже является допустимым значением label `stage` в `RECORDS_PROCESSED_TOTAL` (см. комментарий в metrics.py: `# stage: bronze, silver, gold, quarantined`). Если quarantined records не считаются через этот counter — добавить в Phase 4.

#### 1.5 Исправить corrupted Unicode в dq-v2

Файл: `bioetl-dq-v2.json`

`"Data Flow: Bronze в†™ Silver в†™ Gold"` → `"Data Flow: Bronze → Silver → Gold"`

#### 1.6 Добавить regression tests

Файл: `tests/integration/test_grafana_config.py`

- `test_no_duplicate_variable_names` — нет дублей в `templating.list`
- `test_all_variables_used_in_panels` — каждая переменная используется в ≥1 PromQL query
- `test_quality_ratio_uses_clamp_min` — деление на bronze защищено `clamp_min`
- `test_run_id_variable_source` — `run_id` variable использует метрику, содержащую label `run_id`

---

### Phase 2: Dashboard Modernization

**Priority:** P1
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
- Теги: удалить `"v2"`, `"latest-run"`; очистить избыточные теги (`"working"`, `"active"`, `"minimal"`, `"essential"`)
- **НЕ менять UID** (`bioetl-dq-v2` и т.д.) — чтобы не сломать bookmarks

#### 2.3 Minor fixes

- `refresh`: `"5s"` → `"30s"` в simple dashboard
- Добавить `"links"` секцию с навигацией между 4 дашбордами (по UID)

#### 2.4 Тесты

- `test_datasource_uses_uid_format` — все datasource в `{type, uid}` формате
- `test_unique_panel_ids` — уникальность panel id внутри dashboard

---

### Phase 3: Dashboard Enrichment — Новые Panels

**Priority:** P1
**Scope:** все 4 dashboard JSON
**Метрики — read-only source of truth:** `src/bioetl/infrastructure/observability/metrics.py`

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
- Errors by Stage — `bioetl_errors_total` by `(stage, error_code)` timeseries

Row **"Transform & Storage"**:
- Transform Duration (p95) — `bioetl_transform_duration_seconds` histogram
- Transform Errors — `bioetl_transform_errors_total`
- Bronze Write Duration — `bioetl_bronze_write_duration_seconds`
- Bronze Records Written — `bioetl_bronze_records_written_total`
- Shutdown Events — `bioetl_shutdown_initiated`

#### 3.3 Provider Health Dashboard (`bioetl-provider-health-v2.json`) — +10 panels

Row **"Circuit Breaker"**:
- CB State (state map) — `bioetl_circuit_breaker_state`
- CB Trips — `bioetl_circuit_breaker_trips_total`
- CB Success vs Failure — stacked bar

Row **"API Performance"**:
- API Request Duration (p95) — `bioetl_adapter_request_duration_seconds`
- API Requests by Status — `bioetl_adapter_requests_total`

Row **"HTTP Layer"**:
- HTTP Errors — `bioetl_http_request_errors_total`
- HTTP Retries — `bioetl_http_retries_total`

Row **"Rate Limiting"**:
- Rate Limiter Tokens — `bioetl_rate_limiter_tokens_available`
- Rate Limiter Wait Time (p95) — `bioetl_rate_limiter_wait_seconds`
- Provider Health Status — `bioetl_provider_health_status`

**Также:** заменить fragile `$provider_.*` regex на нормальную template variable из `label_values`.

#### 3.4 Simple Dashboard (`bioetl-simple.json`) — "Operations Glance" (+3 panels)

Оставить существующие 5 panels. Добавить:

| Panel | Type | Metric |
|-------|------|--------|
| Errors | Stat (red when > 0) | `bioetl_errors_total` |
| Pipeline Duration | Stat | `bioetl_pipeline_duration_seconds` |
| Circuit Breaker | Stat (state map) | `bioetl_circuit_breaker_state` |

#### 3.5 Тесты enrichment

- `test_metric_coverage_report` — coverage ≥ 50% метрик из `metrics.py`
- `test_promql_balanced_braces` — сбалансированные `{}`, `[]`, `()` в PromQL
- `test_variable_cascade_order` — переменные, зависящие от других, идут после них

---

### Phase 4: Metric Schema & Observability Pipeline

**Priority:** P1 (решает корневую причину C-1)
**Scope:** `src/bioetl/infrastructure/observability/`, `scripts/`

> Эта фаза выходит за рамки чисто Grafana-рефакторинга и затрагивает infrastructure layer.
> Требует отдельного PR с полным тестовым покрытием.

#### 4.1 Добавить `run_id` в core-метрики

Файл: `src/bioetl/infrastructure/observability/metrics.py`

Добавить label `run_id` в ключевые counters:
- `RECORDS_PROCESSED_TOTAL` — `["pipeline", "stage", "run_type"]` → `["pipeline", "stage", "run_type", "run_id"]`
- `DQ_RECORDS_QUARANTINED_TOTAL` — добавить `run_id`
- `ERRORS_TOTAL` — добавить `run_id`

**Impact analysis:**
- Все callsites `.labels(pipeline=..., stage=..., run_type=...)` должны добавить `run_id=...`
- Увеличивает cardinality — каждый run создаёт новые time series
- Pushgateway `grouping_key` должен включать `run_id`
- Тесты: обновить все unit-тесты метрик

**Альтернатива (minimal):** Не добавлять label в core-метрики, а зафиксировать `run_id` variable query на `bioetl_infrastructure_validated` (уже сделано в Phase 1.2). Тогда `run_id` фильтр будет работать только для preflight-метрик, но не для основных панелей.

> **Рекомендация:** Начать с minimal-подхода (Phase 1.2). Полное добавление `run_id` оформить как отдельную задачу с ADR, т.к. это меняет cardinality model.

#### 4.2 Registry naming — унификация

Файл: `src/bioetl/infrastructure/observability/prometheus_metrics.py`

- Унифицировать ключи: все без `bioetl_` prefix (canonical short name)
- `"bioetl_phase_duration_seconds"` → `"phase_duration_seconds"` и т.д.

#### 4.3 Silent failures — добавить warning

В `PrometheusMetrics.observe_histogram/increment_counter/set_gauge` — логировать warning при неизвестном metric name.

#### 4.4 Demo metrics server — синхронизация

Файл: `docs/03-guides/dashbords/metrics_server.py`

- Синхронизировать label sets с production `metrics.py`
- Удалить несуществующие метрики
- Добавить генерацию DQ, circuit breaker метрик

#### 4.5 Fix script — сделать безопасным

Файл: `scripts/fix_grafana_dashboards.py`

- Merge переменных вместо перезаписи
- `--dry-run` режим
- Идемпотентность

#### 4.6 (Optional) Storage reconciliation metric

Новая gauge-метрика `bioetl_storage_row_count` с labels `["provider", "entity", "layer"]`. Выставляется после записи в Delta Lake по результату `SELECT COUNT(*)`. Позволяет обнаружить расхождение между "отправлено" и "записано".

#### 4.7 (Optional) Pipeline heartbeat gauge

Новая gauge `bioetl_pipeline_active` (1 = running, 0 = idle) с label `["pipeline"]`. Позволяет видеть в реальном времени, какие pipelines выполняются.

---

### Phase 5: Documentation & Docker

**Priority:** P2
**Scope:** docs, docker-compose, prometheus.yml

#### 5.1 Обновить `grafana/README.md`

- Убрать ссылки на v1 dashboards
- Задокументировать новые panels из Phase 3
- Сократить до разумного размера

#### 5.2 Docker и Prometheus

- Удалить deprecated `version: '3.8'` из `docker-compose.monitoring.yml`
- Добавить `extra_hosts: ["host.docker.internal:host-gateway"]` для Linux
- Добавить healthcheck для Prometheus и Grafana сервисов

#### 5.3 (Optional) Observability Contract

Создать `docs/04-reference/observability-contract.md`:
- Обязательные labels для каждого типа метрик
- Единицы измерения (seconds, milliseconds, count)
- Правила именования
- Cardinality guidelines (max unique label combinations)

Цель: предотвратить деградацию мониторинга при добавлении новых pipelines.

#### 5.4 Документация cleanup

- Консолидировать changelog-style файлы (TIMESTAMP_FIXED.md, INFO_PANELS_ADDED.md и т.д.)
- Целевое количество doc файлов: ≤ 6 (из текущих 16)

---

### Phase 6: DQ Baseline Automation (Optional, P3)

**Scope:** `scripts/dq_baseline_update.py`, `src/bioetl/infrastructure/observability/anomaly/`

> Вынесено в отдельную фазу, т.к. требует архитектурного решения (ADR).

#### 6.1 Проблема

`scripts/dq_baseline_update.py` работает с локальными JSON в `data/audit/` и `data/metrics/`. Полностью отключён от Prometheus и DQMonitor. Baselines устаревают и не обновляются автоматически.

#### 6.2 Решение

Модифицировать `DataQualityMonitor` (implements `DQMonitorPort`):
- Pre-flight: подтягивать актуальные baseline из Prometheus (query `avg_over_time(bioetl_dq_validation_score[7d])`)
- Post-run: автоматически обновлять baseline на основе результатов текущего run (если run успешен)
- Deprecate `dq_baseline_update.py` после миграции

---

### Phase 7: Final Verification

#### 7.1 Автоматическая верификация
```bash
# Все integration-тесты зелёные
python -m pytest tests/integration/test_grafana_config.py -v -o "addopts="

# JSON validity
python -c "import json; [json.load(open(f)) for f in __import__('glob').glob('grafana/dashboards/*.json')]"

# Mypy (если затрагивали metrics.py / prometheus_metrics.py)
mypy --strict src/bioetl/infrastructure/observability/
```

#### 7.2 Ручная верификация
```bash
# Запустить monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Запустить pipeline с реальными метриками
bioetl run chembl_molecule --limit 100

# Проверить в Grafana (http://localhost:3000):
# 1. Все 4 дашборда загружаются без ошибок
# 2. Template variable $run_id populated (не пустой dropdown)
# 3. Новые panels показывают данные
# 4. DQ dashboard показывает реальные DQ-метрики
# 5. Provider Health показывает circuit breaker, HTTP errors
# 6. Dashboard links навигируют корректно
# 7. Quality Ratio учитывает quarantined записи
```

---

## Execution Order & Dependencies

```
Phase 1 (critical bugs + tests)
    │
    ▼
Phase 2 (modernization)
    │
    ▼
Phase 3 (enrichment + tests)
    │               │
    ▼               ▼
Phase 4          Phase 5
(schema +        (docs +
 infra)          docker)
    │               │
    └───────┬───────┘
            ▼
     [Phase 6 — optional]
            │
            ▼
      Phase 7 (verification)
```

Phase 4 и Phase 5 можно выполнять параллельно.
Phase 6 (baseline automation) — опциональная, может быть отдельным PR.

---

## Key Files

| File | Access | Phase |
|------|--------|-------|
| `grafana/dashboards/bioetl-simple.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-overview-v2.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-dq-v2.json` | R/W | 1, 2, 3 |
| `grafana/dashboards/bioetl-provider-health-v2.json` | R/W | 1, 2, 3 |
| `tests/integration/test_grafana_config.py` | R/W | 1, 2, 3 |
| `src/bioetl/infrastructure/observability/metrics.py` | R/W | 4 (schema change) |
| `src/bioetl/infrastructure/observability/prometheus_metrics.py` | R/W | 4 |
| `docs/03-guides/dashbords/metrics_server.py` | R/W | 4 |
| `scripts/fix_grafana_dashboards.py` | R/W | 4 |
| `scripts/dq_baseline_update.py` | R/W | 6 |
| `grafana/provisioning/datasources/prometheus.yml` | R/O | reference |
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
| `run_id` variable functional | 0/4 dashboards | 4/4 |
| DQ metrics on DQ dashboard | 0 | 8 |
| Provider metrics on Provider dashboard | 2 | 12 |
| Quality formula includes quarantined | no | yes |
| Integration test count (dashboard) | 3 | ≥ 12 |
| Doc files in dashbords/ | 16 | ≤ 6 |

---

## Comparison of 3 Source Plans

| Aspect | Plan 1 (Audit) | Plan 2 (Alternative) | Plan 3 (Analytics) | Consolidated |
|--------|---------------|---------------------|-------------------|--------------|
| `run_id` root cause | "unused variable" | "unused variable" | **Schema gap** — label missing in metrics | Phase 1.2 (workaround) + Phase 4.1 (full fix) |
| Aggregation issue | Not identified | Not identified | **`sum()` + Pushgateway** = false accumulation | Phase 4.1 note |
| DQ formula | Gold/Bronze | Gold/Bronze | **(Gold+Quarantined)/Bronze** | Phase 1.4 |
| Baseline automation | Not identified | Not identified | **Pre-flight from Prometheus** | Phase 6 |
| Storage reconciliation | Not identified | Not identified | **Post-write row count** | Phase 4.6 |
| Observability contract | Not identified | Not identified | **Formal label/unit spec** | Phase 5.3 |
| Dashboard-as-Code | Not identified | Not identified | grafanalib (optional) | Deferred |
| Panel specifications | General | **Concrete (+8, +10, +10, +3)** | General | Phase 3 |
| Test placement | End (Phase 9) | **TDD — with fixes** | Not specified | With fixes |
| Simple dashboard | Delete | **Keep + extend** | Not specified | Keep as "Glance" |
| Demo server | Fix schema | Not covered | Not covered | Phase 4.4 |
| Fix script | Refactor | Not covered | Not covered | Phase 4.5 |
| Registry naming | Unify keys | Not covered | Not covered | Phase 4.2 |
| Phase count | 9 | 5 | 5 | **7** (2 optional) |
