# BioETL Observability Specification (DD)

Этот документ фиксирует **каноническую** спецификацию наблюдаемости BioETL по состоянию на **2026-03-26**.

- Статус: `active`
- Версия: `3.2.0`
- Scope: `logs + metrics + tracing + correlation + provider health + control plane + traceability`
- Source of truth: код в `src/bioetl/**/observability*`, `src/bioetl/application/observability/*`, `src/bioetl/infrastructure/adapters/http/*`

## 1. Verification Evidence

Проверка выполнена по коду командами:

```bash
rg --files src/bioetl/infrastructure/observability src/bioetl/composition/bootstrap src/bioetl/infrastructure/adapters/http docs grafana
rg -n "observability|metrics|trace|X-Correlation-ID|provider_health|rate_limit|health_check" src/bioetl -g '*.py'
sed -n '1,220p' src/bioetl/infrastructure/observability/logging_config.py
sed -n '1,320p' src/bioetl/infrastructure/observability/unified_logger.py
sed -n '1,320p' src/bioetl/infrastructure/observability/_metrics_defs_*.py
sed -n '1,340p' src/bioetl/infrastructure/observability/prometheus_metrics.py
sed -n '1,320p' src/bioetl/domain/types/enums.py
sed -n '1,320p' src/bioetl/application/observability/observer.py
sed -n '1,320p' src/bioetl/application/observability/observer_context_mixin.py
sed -n '1,320p' src/bioetl/infrastructure/adapters/http/client_context_mixin.py
sed -n '1,320p' configs/providers/{chembl,pubchem,pubmed,crossref,openalex,semanticscholar,uniprot}.yaml
```

Ключевые пути:

- `src/bioetl/infrastructure/observability/logging_config.py`
- `src/bioetl/infrastructure/observability/unified_logger.py`
- `src/bioetl/infrastructure/observability/_metrics_defs_*.py`
- `src/bioetl/infrastructure/observability/prometheus_metrics.py`
- `src/bioetl/domain/types/enums.py`
- `src/bioetl/application/observability/observer.py`
- `src/bioetl/infrastructure/adapters/http/client_context_mixin.py`

## 2. Canonical Conventions

### 2.1 Metric naming

- Prefix: `bioetl_`
- Case: `snake_case`
- Counters: suffix `_total`
- Units in name: `_seconds`, `_ms`, `_bytes`, `_records`
- Prometheus exposition endpoint: `http://localhost:${BIOETL_METRICS_PORT:-8000}/metrics`

Важно: `kebab-case` вида `bioetl-pipeline-duration-seconds` считается legacy и неканоничным.

### 2.2 Logging schema

`UnifiedLogger` обеспечивает обязательные поля контекста:

- `run_id`
- `pipeline`
- `stage` (default: `init`)

Поля записи:

- `event` (первый positional аргумент логгера)
- `level`
- время: фактически сейчас выводится `timestamp` (через `structlog.processors.TimeStamper(fmt="iso")`)

Правило совместимости:

- Каноническое runtime-поле времени: `timestamp`
- Переходный alias `ts` допустим только на уровне downstream-нормализации

### 2.3 Correlation

- Сквозной correlation ID: `run_id`
- HTTP клиент добавляет заголовок `X-Correlation-ID: <run_id>` при наличии `run_id`
- Tracing span attributes включают `bioetl.run_id`

## 3. Runtime Metrics Contract

Полный каталог метрик задаётся в `src/bioetl/infrastructure/observability/_metrics_defs_*.py` и экспортируется через `metrics_definitions.py`.

Текущий размер каталога: **72** метрики (`metrics_export_names.py`).

Ниже обязательное ядро (MUST для мониторинга запусков):

| Metric | Type | Labels | Notes |
|---|---|---|---|
| `bioetl_pipeline_runs_total` | Counter | `pipeline,run_type,status` | `status` в коде: `success`, `failed`, `shutdown` |
| `bioetl_pipeline_duration_seconds` | Histogram | `pipeline,stage,status,run_type` | Длительности run/stage |
| `bioetl_phase_duration_seconds` | Histogram | `pipeline,phase,status` | Lifecycle-фазы |
| `bioetl_control_plane_manifest_writes_total` | Counter | `pipeline,run_type,status` | Попытки записи immutable run manifest |
| `bioetl_control_plane_ledger_appends_total` | Counter | `pipeline,event_type,status` | Попытки append в run ledger |
| `bioetl_checkpoint_compatibility_events_total` | Counter | `pipeline,disposition` | Итоги resume/checkpoint compatibility policy |
| `bioetl_lineage_fragments_emitted_total` | Counter | `pipeline,layer,status` | Попытки публикации lineage fragments |
| `bioetl_records_processed_total` | Counter | `pipeline,stage,run_type` | throughput |
| `bioetl_errors_total` | Counter | `pipeline,stage,error_code` | taxonomy входа |
| `bioetl_http_request_duration_seconds` | Histogram | `provider,method,status` | HTTP latency |
| `bioetl_http_request_errors_total` | Counter | `provider,method,error_type` | HTTP errors |
| `bioetl_data_source_retry_exhausted_total` | Counter | `provider,operation` | exhausted retries |
| `bioetl_provider_health_status` | Gauge | `provider` | см. mapping ниже |
| `bioetl_circuit_breaker_state` | Gauge | `adapter` | 0/1/2 mapping |
| `bioetl_dq_validation_score` | Gauge | `pipeline,entity` | 0..1 |
| `bioetl_data_freshness_seconds` | Gauge | `pipeline,entity` | unix ts последнего успеха |

Guardrail для новых метрик control-plane/traceability:

- не использовать `run_id`, `manifest_id`, filesystem paths, `batch_id` и другие
  high-cardinality идентификаторы как Prometheus labels;
- агрегировать по `pipeline`, `run_type`, `event_type`, `layer`, `status`,
  `disposition`, а детализацию по конкретному запуску получать через
  `run-manifest show` и sidecar/control-plane артефакты.

### 3.1 Enum mappings

Канонические mapping из кода:

- `HealthStatus.to_metric_value()` (`src/bioetl/domain/types/enums.py`):
  - `UNHEALTHY -> 0`
  - `DEGRADED -> 1`
  - `HEALTHY -> 2`
- `CircuitBreakerState.to_metric_value()`:
  - `CLOSED -> 0`
  - `HALF_OPEN -> 1`
  - `OPEN -> 2`

## 4. Tracing Contract

- По умолчанию: `NoOpTracing` (tracing disabled)
- При `BIOETL_OBSERVABILITY__TRACING_ENABLED=true`: `OpenTelemetryTracer`
- Exporter:
  - OTLP exporter при установленном OTLP пакете
  - fallback: Console exporter

Текущее состояние:

- Спаны создаются на pipeline и HTTP-операциях
- `logging_config.py` автоматически добавляет `trace_id` и `span_id` в structlog-записи,
  если в текущем контексте есть активный OTel span
- При отключённом tracing или отсутствии активного span лог-схема деградирует
  безопасно: поля `trace_id`/`span_id` просто не добавляются

## 5. Provider Rate-Limit Baseline (as configured)

Значения ниже берутся из `configs/providers/*.yaml` и отражают **текущую конфигурацию репозитория**, не внешние SLA провайдеров.

| Provider | Base RPS | Burst | API-key override |
|---|---:|---:|---|
| chembl | 3 | 10 | - |
| pubchem | 5.0 | 10 | - |
| pubmed | 3.0 | 5 | `10 / 20` |
| crossref | 50 | 100 | polite pool flag |
| openalex | 10 | 20 | polite pool flag |
| semanticscholar | 0.1 | 1 | `1.0 / 5` |
| uniprot | 10.0 | 20 | `100 / 200` |

## 6. Alert Threshold Baseline

Рекомендуемая минимальная таблица (runbook links локальные):

| Metric | Condition | Severity | Runbook |
|---|---|---|---|
| `bioetl_pipeline_runs_total{status="failed"}` | `increase(...) > 0` за `15m` | P1 | `docs/05-operations/runbooks/pipeline-failure-critical.md` |
| `bioetl_control_plane_manifest_writes_total{status="failed"}` | `increase(...) > 0` за `15m` | P1 | `docs/05-operations/runbooks/run-manifest-inspection.md` |
| `bioetl_control_plane_ledger_appends_total{status="failed"}` | `increase(...) > 0` за `15m` | P1 | `docs/05-operations/runbooks/run-manifest-inspection.md` |
| `bioetl_pipeline_health_check_passed` | `== 0` за `5m` | P1 | `docs/05-operations/runbooks/pipeline-failure-critical.md` |
| `bioetl_provider_health_status` | `== 0` за `5m` | P2 | `docs/05-operations/runbooks/incident-response.md` |
| `bioetl_circuit_breaker_state` | `== 2` за `5m` | P2 | `docs/05-operations/runbooks/incident-response.md` |
| `bioetl_dq_validation_score` | `< 0.80` на запуск | P2 | `docs/05-operations/runbooks/pipeline-failure-dq.md` |
| `bioetl_checkpoint_compatibility_events_total{disposition=~".*_incompatible"}` | `increase(...) > 0` за `30m` | P2 | `docs/05-operations/runbooks/checkpoint-debugging.md` |
| `bioetl_lineage_fragments_emitted_total{status="failed"}` | `increase(...) > 0` за `15m` | P2 | `docs/05-operations/runbooks/traceability-signal-ownership.md` |
| `bioetl_data_source_retry_exhausted_total` | `increase(...) > 0` за `1h` | P2 | `docs/05-operations/runbooks/incident-response.md` |
| `bioetl_rate_limiter_wait_seconds` | `histogram_quantile(0.95, ...) > 1` за `10m` | P3 | `docs/05-operations/runbooks/observability-checklist.md` |

## 7. Error Taxonomy (domain canonical)

Коды ошибок из `ErrorType` (`src/bioetl/domain/types/enums.py`):

- Critical: `AUTH_FAILURE`, `DB_UNAVAILABLE`, `SCHEMA_MISMATCH_GOLD`, `SCHEMA_EVOLUTION`, `LOCK_LOST`
- Recoverable: `RATE_LIMIT`, `TIMEOUT`, `NETWORK_ERROR`
- Data quality: `SCHEMA_VIOLATION`, `INVALID_DATA`, `MISSING_REQUIRED_FIELD`, `DATA_QUALITY`

## 8. Known Drifts and Required Follow-ups

| ID | Severity | Drift | Evidence |
|---|---|---|---|
| OBS-001 | HIGH | Часть docs использует `bioetl-...` вместо `bioetl_...` | `docs/02-architecture/observability-layers.md`, `docs/05-operations/runbooks/observability-checklist.md` |
| OBS-002 | HIGH | `provider_health_status` docstring в `_metrics_defs_adapter.py` противоречит enum mapping | `src/bioetl/infrastructure/observability/_metrics_defs_adapter.py`, `src/bioetl/domain/types/enums.py` |
| OBS-003 | MEDIUM | `ts` в текстах, но runtime выводит `timestamp` | `logging_config.py` vs doc/comments |
| OBS-004 | MEDIUM | `run_id` присутствует в label у preflight/infra gauge (высокая кардинальность) | `_metrics_defs_health.py` |

## 9. Definition of Done for observability doc sync

- Все спецификации/чеклисты используют `bioetl_...` naming
- Во всех docs используется `run_id` (не `run-id`)
- Mapping для `provider_health_status` совпадает с `HealthStatus.to_metric_value()`
- Поле времени в лог-схеме описано как `timestamp` (или явно как dual-mode `timestamp/ts`)
- Алерты используют реальные `status` (`failed`, `success`, `shutdown`) из runtime
- Log/trace correlation через `trace_id` и `span_id` соответствует runtime processor chain
