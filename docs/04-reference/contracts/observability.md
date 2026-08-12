______________________________________________________________________

Version: 1.0.4
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-19'

______________________________________________________________________

# BioETL Observability Specification (DD)

Этот документ фиксирует **каноническую** спецификацию наблюдаемости BioETL по состоянию на **2026-07-19**.

- Статус: `active`
- Версия: `3.5.2`
- Scope: `logs + metrics + tracing + correlation + provider health + control plane + audit + traceability`
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

Канонические contract suites для explicit port verification:

- `tests/unit/infrastructure/observability/test_logger_port_contract.py`
- `tests/unit/infrastructure/observability/test_metrics_port_contract.py`
- `tests/unit/infrastructure/observability/test_tracing_port_contract.py`
- Shipped Grafana dashboards (`grafana/dashboards/*.json`, 7 UIDs) and
  `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`: `bioetl-control-plane-v1`,
  `bioetl-overview-v2`, `bioetl-runtime`, `bioetl-provider-health-v2`,
  `bioetl-dq-v2`, `bioetl-incident-v1`, and `bioetl-run-explorer-v1`
- `bioetl-workflow-overview` and `bioetl-alerts-slo` are retired, not shipped;
  workflow diagnosis lives in Pipeline Diagnostics and alert triage lives in
  Incident Workspace (see `docs/03-guides/dashboards/panel-title-inventory.md`)

## 2. Canonical Conventions

Cross-links for canonical observability governance:

- Architecture decision: [ADR-017](../../02-architecture/decisions/ADR-017-observability-architecture.md)
- Layer responsibilities: [Observability Layers](../../02-architecture/observability-layers.md)
- Operator validation path: [Observability Checklist](../../05-operations/runbooks/observability-checklist.md)

### 2.1 Metric naming

- Prefix: `bioetl_`
- Case: `snake_case`
- Counters: suffix `_total`
- Units in name: `_seconds`, `_ms`, `_bytes`, `_records`
- Prometheus exposition endpoint: `http://localhost:${BIOETL_METRICS_PORT:-8000}/metrics`

Важно: `kebab-case` вида `bioetl-pipeline-duration-seconds` считается legacy и неканоничным.

### 2.1.1 Label normalization

- `endpoint` для adapter request metrics MUST публиковаться как bounded
  route-template (`/works/{id}`, а не `/works/123456789`)
- `source_kind` для filter metrics MUST публиковаться как bounded vocabulary
  (`csv_single_column`, `csv_multi_column`, `direct_ids`, `direct_multi_ids`, `other`);
  raw file/path identity MUST NOT be used as a Prometheus label
  token; raw paths и user/data-dependent filenames outside the bounded token
  shape запрещены
- `operation` для adapter fallback/retry/error families MUST использовать
  reviewed bounded vocabulary; неизвестные значения схлопываются в `other`
- runtime `stage`/`phase` labels MUST использовать canonical bounded vocabularies
  rather than free-text ad hoc values

Canonical ordinary lifecycle phases:

- `startup`
- `preflight`
- `lifecycle_clear`
- `execution`
- `postrun`
- `cleanup`

Canonical composite/runtime phase additions:

- `preflight_validation`
- `seed`
- `dependencies`
- `enrichment`
- `merge`
- `cross_validation`
- `gold_write`

### 2.2 Logging schema

`UnifiedLogger` обеспечивает обязательные поля контекста:

- `run_id`
- `pipeline`
- `stage` (default: `init`)

Поля записи:

- `event` (первый positional аргумент логгера)
- `level`
- время: фактически сейчас выводится `timestamp` (через `structlog.processors.TimeStamper(fmt="iso")`)

Оставшиеся explicit compatibility behaviors:

- Каноническое runtime-поле времени: `timestamp`
- Переходный alias `ts` допустим только на уровне downstream-нормализации
- Канонический structured logging path использует flat top-level поля
- `extra={...}` разрешён только как compatibility input и должен
  разворачиваться в top-level runtime payload; явные kwargs имеют приоритет над
  вложенными значениями

### 2.3 Correlation

- Сквозной correlation ID: `run_id`
- HTTP клиент добавляет заголовок `X-Correlation-ID: <run_id>` при наличии `run_id`
- Tracing span attributes включают `bioetl.run_id`

### 2.4 Application lifecycle and DQ contract

- `PipelineObserver` является каноническим lifecycle emitter для ordinary
  pipeline runs
- ordinary preflight runtime publication is observer-owned: application helpers
  such as `PreflightService` and `HealthAggregator` may build typed reports, but
  phase-adjacent logs/metrics for ordinary runs must be emitted from the runner
  through `PipelineObserver`
- typed aggregate Domain Events из `bioetl.domain.aggregates.events` имеют
  explicit canonical projection в runtime observability vocabulary через
  `bioetl.domain.observability_event_mapping` и могут эмититься через
  `PipelineObserver.emit_domain_event(...)` без введения отдельного event bus
- frozen code-level contract для runtime event publication задаётся в
  `bioetl.domain.runtime_observability_publication_contract`; канонические
  emitters ограничены `PipelineObserver.emit_event` и
  `PipelineObserver.emit_domain_event`
- direct logger-only publication не считается canonical path для lifecycle /
  typed domain events; structured logs/metrics/spans являются side effects
  canonical observer emission
- `bioetl_observability_events_total` является observer-owned metric family и
  не должен использоваться infrastructure-local retry/final telemetry helpers;
  storage/control-plane operational telemetry обязана публиковаться через
  dedicated bounded metric families, а не через unified runtime event counter
- helper-local preflight reporting modules are not a sanctioned runtime
  publication path for ordinary pipeline runs
- Lifecycle phase emissions используют low-cardinality `phase` labels и не
  подменяются ad-hoc logging-only path
- `MetricsPort` остаётся transport-level observability port; pipeline-specific
  helper semantics должны жить в application-level facade/helper, а не в самом
  generic port contract
- `DQMonitorPort.check_quality()` возвращает typed domain anomalies:
  `list[DQAnomaly]`
- канонический timestamp для `DQMonitorPort.check_quality(...)` и
  `DQMonitorPort.update_baseline_from_metrics(...)` принадлежит application
  layer и выводится из `freshness_anchor_timestamp` / ingestion anchor
  текущего run; infrastructure adapter не должен silently invent отдельный
  anomaly timestamp
- Postrun observability должна использовать structured spans/events для
  compaction, DQ evaluation, DQ report generation, vacuum и final metadata
- `AuditPort` остаётся отдельным traceability/observability port и
  инжектируется в Bronze/Silver/Gold runtime wiring из composition layer
- `ObservabilityBundle` является canonical runtime carrier для `logger`,
  `metrics`, `tracer` и `audit`; PipelineRunnerService bootstrap и medallion
  storage wiring должны получать один и тот же injected `AuditPort`, а не
  собирать независимые audit adapters локально
- production runtime observability bootstrap is fail-closed by default:
  `NoOpLogger`, `NoOpMetrics`, `NoOpTracing`, and `NoOpAudit` are rejected in
  `env=prod` unless
  `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true` is set
- production runtime observability bootstrap MUST also validate the configured
  control-plane persistence profile against the same manifest / ledger /
  lineage-sidecar invariants used by runtime builder helpers; bootstrap must
  not maintain a divergent second rule set
- terminal Domain Event timestamps MUST be derived from the observer's captured
  `wall_start_time` plus monotonic duration; missing `wall_start_time` is an
  explicit observer invariant violation, not a trigger for `datetime.now()`
- replay-facing composite/admin/public execution results MUST derive
  `completed_at` from the captured `started_at` anchor plus monotonic duration
  as well; terminal result assembly must not invent a separate wall-clock
  completion timestamp after the run has already finished

## 3. Runtime Metrics Contract

Полный каталог метрик задаётся в `src/bioetl/infrastructure/observability/_metrics_defs_*.py`
и собирается через `prometheus_metric_registries.py`.

Канонический inventory metric families выводится из runtime registry surface
`REGISTERED_PROMETHEUS_METRIC_NAMES` в
`src/bioetl/infrastructure/observability/prometheus_metric_registries.py`
плюс explicit recording-rule declaration surface в
`configs/quality/observability_metric_declarations.yaml`.
Для repo-local reconciliation docs/runtime/rules drift используйте:
`python -m scripts.engineering.qa report-observability-metric-inventory --json`.

### 3.1 Prometheus descriptor authority

Code-level metric definitions assembled by
`src/bioetl/infrastructure/observability/prometheus_metric_registries.py` are
the authoritative source for every `bioetl_*` metric `HELP` text and `TYPE`.
Both the direct `/metrics` exposition and the restricted registry published to
Pushgateway MUST preserve those descriptors. Prometheus
`/api/v1/metadata?metric=<name>` is deployment evidence that scrape and
transport preserved the contract; it is not a second source of truth. A
missing metadata response is therefore `unavailable` evidence and must not be
silently interpreted as an untyped metric.

Inside the shipped monitoring network Prometheus MUST scrape the service name
`pushgateway:9091`. `localhost:9091` remains valid only for host-side clients
publishing through the exposed port.

Ниже обязательное ядро (MUST для мониторинга запусков):

| Metric                                         | Type      | Labels                                      | Notes                                                                                                                                                                         |
| ---------------------------------------------- | --------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bioetl_pipeline_runs_total`                   | Counter   | `pipeline,run_type,status`                  | `status` в коде: `success`, `failed`, `shutdown`                                                                                                                              |
| `bioetl_pipeline_duration_seconds`             | Histogram | `pipeline,stage,status,run_type`            | Длительности run/stage                                                                                                                                                        |
| `bioetl_phase_duration_seconds`                | Histogram | `pipeline,phase,status`                     | Lifecycle-фазы                                                                                                                                                                |
| `bioetl_control_plane_manifest_writes_total`   | Counter   | `pipeline,run_type,status`                  | Попытки записи immutable run manifest                                                                                                                                         |
| `bioetl_control_plane_ledger_appends_total`    | Counter   | `pipeline,event_type,status`                | Попытки append в run ledger                                                                                                                                                   |
| `bioetl_control_plane_terminal_events_total`   | Counter   | `pipeline,terminal_status`                  | Bounded terminal run outcomes mirrored from persisted run-ledger entries (`success`, `failed`, `shutdown`)                                                                  |
| `bioetl_manifest_ledger_integrity_ratio`       | Gauge     | `pipeline,run_type,integrity_type`          | Complementary `consistent` / `inconsistent` ratios over manifests that expect a ledger; `run_ledger_enabled=false` manifests are excluded and zero denominator is never reported as healthy |
| `bioetl_replay_reconstructability_events_total`| Counter   | `pipeline,replay_capability,strict_requirement,status` | Bounded replay reconstructability decisions emitted during manifest assembly                                                                                                   |
| `bioetl_replay_duplicate_overwrite_risk_total` | Counter   | `pipeline,run_type,risk_type`               | Accepted replay manifests with bounded `duplicate` / `overwrite` write risk; both series are initialized with `inc(0)` after durable manifest acceptance |
| `bioetl_checkpoint_compatibility_events_total` | Counter   | `pipeline,disposition`                      | Итоги resume/checkpoint compatibility policy                                                                                                                                  |
| `bioetl_checkpoint_load_events_total`          | Counter   | `pipeline,status`                           | Bounded checkpoint load decisions (`loaded`, `missing`, `blocked`, `incompatible`, `observe_blocked_identity`, `observe_loaded_degraded`, `incompatible_hard_fail`, `failed`) |
| `bioetl_checkpoint_operator_operations_total`  | Counter   | `operation,status`                          | Bounded checkpoint admin actions for `list`, `get`, and `delete` workflows                                                                                                    |
| `bioetl_checkpoint_operator_duration_seconds`  | Histogram | `operation,status`                          | Latency of checkpoint admin/operator workflows                                                                                                                                |
| `bioetl_checkpoint_save_events_total`          | Counter   | `pipeline,operation,status`                 | Bounded checkpoint save outcomes across ordinary and composite persistence paths                                                                                              |
| `bioetl_checkpoint_save_duration_seconds`      | Histogram | `pipeline,operation,status`                 | Latency of checkpoint save attempts and failures                                                                                                                              |
| `bioetl_memory_pressure_events_total`          | Counter   | `pipeline,stage,reason,monitor_mode,status` | Adaptive-memory decisions that observed active pressure; labels stay bounded to stage, bounded monitor mode, bounded reason, and bounded decision status                      |
| `bioetl_memory_batch_resize_events_total`      | Counter   | `pipeline,stage,reason,monitor_mode,status` | Adaptive-memory decisions that changed batch size during pressure handling or recovery                                                                                        |
| `bioetl_memory_monitor_fallback_events_total`  | Counter   | `pipeline,stage,reason,monitor_mode,status` | Adaptive-memory decisions emitted while monitor mode used bounded fallback paths (`resource`, `estimate`, `unknown`)                                                          |
| `bioetl_memory_pressure_state`                 | Gauge     | `pipeline,stage,reason,monitor_mode,status` | Latest bounded adaptive-memory pressure state for the emitted decision (`1` under pressure, `0` otherwise)                                                                    |
| `bioetl_lineage_fragments_emitted_total`       | Counter   | `pipeline,layer,status`                     | Попытки публикации lineage fragments                                                                                                                                          |
| `bioetl_lineage_refs_missing_total`            | Counter   | `pipeline,layer,ref_type`                   | Missing upstream lineage references detected during persistence                                                                                                               |
| `bioetl_composite_source_selection_total`      | Counter   | `pipeline,decision_type,selected_source`    | Low-cardinality composite source-selection decisions recorded during persistence                                                                                              |
| `bioetl_control_plane_reads_total`             | Counter   | `store,operation,status`                    | Срез outcomes manifest/ledger/lineage lookup paths для success/miss/fail агрегатов                                                                                            |
| `bioetl_metrics_publication_events_total`      | Counter   | `pipeline,run_type,target,status`           | Best-effort metrics publication attempts for endpoint / Pushgateway targets and their bounded outcomes                                                                       |
| `bioetl_observability_runtime_status`          | Gauge     | `pipeline,component,mode`                   | Active runtime mode for observability components (`logger`, `metrics`, `tracing`, `audit`, `dq_monitor`)                                                                    |
| `bioetl_output_artifact_publication_events_total` | Counter | `pipeline,stage,status`                     | bounded output artifact publication outcomes for Bronze/Silver/Gold metadata sidecars; `disabled` is explicit when no artifact recorder is attached                          |
| `bioetl_records_processed_total`               | Counter   | `pipeline,stage,run_type`                   | throughput                                                                                                                                                                    |
| `bioetl_record_flow_records_total`             | Counter   | `pipeline,run_type,flow_stage`              | bounded record-flow projection for `fetched/bronze/silver/gold/filtered_out/quarantined`; not a replacement for manifest/ledger or canonical DQ quarantine truth          |
| `bioetl_record_flow_invariants_total`          | Counter   | `pipeline,run_type,invariant,status`        | bounded terminal invariant outcomes for `fetched_equals_bronze`, `bronze_partitioned`, `silver_gold_monotonic`; runtime alert/rule surface, not forensic truth            |
| `bioetl_stage_records_total`                   | Counter   | `pipeline,run_type,stage,outcome`           | canonical stage-model projection for `input/ingestion/transform/validation/storage/output` and bounded record-accounting outcomes (`bronze/records`, `silver/valid|quarantined|skipped|filtered_out|deduplicated`, `gold/written|quarantined|skipped|excluded_by_contract|deduplicated`) |
| `bioetl_processed_records_*_current`           | Recording rules | `pipeline,run_type`                    | current 15m Processed Records reconciliation rows/deltas derived from `bioetl_stage_records_total`; no `$__range`, no `run_id`, and missing accounting series are no-data/UNKNOWN rather than OK                                              |
| `bioetl_processed_records_reconciliation_status` | Recording rule | `pipeline,run_type`                  | Processed Records reconciliation status: `0=UNKNOWN`, `1=OK`, `2=DEGRADED`, `3=FAILING`                                                                                        |
| `bioetl_stage_backlog_records`                 | Gauge     | `pipeline,run_type,stage`                   | bounded unresolved stage backlog at terminal projection time                                                                                                                  |
| `bioetl_stage_lag_seconds`                     | Gauge     | `pipeline,run_type,stage`                   | bounded unresolved stage lag derived from run wall-clock anchor; `0` when no backlog is present                                                                               |
| `bioetl_batch_lifecycle_events_total`          | Counter   | `pipeline,run_type,event,stage,status`      | bounded batch lifecycle events for `created`, `written`, `failed` across Bronze/Silver/Gold runtime projections                                                              |
| `bioetl_batch_lifecycle_records_total`         | Counter   | `pipeline,run_type,event,stage,status`      | bounded record totals attached to the same batch lifecycle events                                                                                                             |
| `bioetl_workflow_pipeline_verdict_status`      | Recording rule | `pipeline,run_type`                    | first-screen workflow dashboard pipeline verdict: `0=OK`, `1=WARN`, `2=CRIT`; failed pipeline-run increments in the 15m rule window override later success/completed increments |
| `bioetl_composite_phase_records_total`         | Counter   | `pipeline,phase,outcome`                    | bounded composite-phase record counters for `seed`, `dependencies`, `enrichment`, and `merge`                                                                                |
| `bioetl_composite_phase_errors_total`          | Counter   | `pipeline,phase,error_kind`                 | bounded composite-phase error counters for `failed`, `timeout`, and `record_error`                                                                                            |
| `bioetl_composite_phase_loss_total`            | Counter   | `pipeline,phase,loss_kind`                  | bounded composite-phase loss counters for `unwritten`, `not_found`, `partially_enriched`, and `quarantined`                                                                  |
| `bioetl_composite_phase_retries_total`         | Counter   | `pipeline,phase,retry_kind`                 | bounded composite-phase retry/resume counters; currently `resume` is the canonical runtime projection                                                                         |
| `bioetl_errors_total`                          | Counter   | `pipeline,stage,error_code`                 | taxonomy входа                                                                                                                                                                |
| `bioetl_adapter_request_duration_seconds`      | Histogram | `provider,endpoint`                         | adapter request latency by provider endpoint                                                                                                                                  |
| `bioetl_http_request_duration_seconds`         | Histogram | `provider,method,status`                    | HTTP latency                                                                                                                                                                  |

BatchStatus aggregate is non-runtime observability source today: the domain
aggregate states (`open`, `sealed`, `writing`, `committed`, `failed`) are
validated in `bioetl.domain.aggregates.Batch`, but runtime batch processing emits
typed lifecycle events and the bounded `bioetl_batch_lifecycle_*` projections
instead of maintaining a live aggregate instance. Do not add a synthetic runtime
batch-status gauge until the write path adopts the aggregate transitions as the
source of truth.
| `bioetl_http_request_errors_total`             | Counter   | `provider,method,error_type`                | HTTP errors                                                                                                                                                                   |
| `bioetl_health_check_latency_seconds`          | Histogram | `provider`                                  | Canonical provider health-check latency metric family (seconds only)                                                                                                          |
| `bioetl_data_source_retry_exhausted_total`     | Counter   | `provider,operation`                        | exhausted retries                                                                                                                                                             |
| `bioetl_provider_health_status`                | Gauge     | `provider`                                  | см. mapping ниже                                                                                                                                                              |
| `bioetl_circuit_breaker_state`                 | Gauge     | `adapter`                                   | 0/1/2 mapping                                                                                                                                                                 |
| `bioetl_rate_limiter_wait_seconds`             | Histogram | `provider`                                  | provider rate-limiter wait latency                                                                                                                                            |
| `bioetl_rate_limiter_tokens_available`         | Gauge     | `provider`                                  | current available provider rate-limiter tokens                                                                                                                                |
| `bioetl_dq_validation_score`                   | Gauge     | `pipeline,entity`                           | 0..1                                                                                                                                                                          |
| `bioetl_dq_dispositions_total`                 | Counter   | `pipeline,stage,disposition,terminal_status` | bounded DQ disposition outcomes with terminal correlation for `pass`, `quarantine`, and `hard_fail` paths                                                                   |
| `bioetl_data_freshness_seconds`                | Gauge     | `pipeline,entity`                           | unix timestamp ingestion anchor успешного запуска (сейчас `PipelineContext.started_at`); age считается как `time() - metric`                                                  |
| `bioetl_quarantine_operator_operations_total`  | Counter   | `operation,status`                          | bounded operator actions for inspect/replay/purge/update workflows                                                                                                            |
| `bioetl_quarantine_operator_duration_seconds`  | Histogram | `operation,status`                          | latency of quarantine operator workflows                                                                                                                                      |
| `bioetl_postrun_phase_events_total`            | Counter   | `pipeline,phase,status`                     | bounded postrun subphase outcomes for `dq_evaluation`, `dq_reports`, `compaction`, `vacuum`, `final_metadata`                                                                 |
| `bioetl_postrun_phase_duration_seconds`        | Histogram | `pipeline,phase,status`                     | bounded durations for the same postrun subphases                                                                                                                              |
| `bioetl_audit_write_events_total`              | Counter   | `layer,operation,status`                    | bounded outcomes for file-backed audit persistence                                                                                                                            |
| `bioetl_audit_write_duration_seconds`          | Histogram | `layer,operation,status`                    | latency of file-backed audit persistence                                                                                                                                      |
| `bioetl_audit_query_events_total`              | Counter   | `layer_filter,status`                       | bounded outcomes for audit inspection/query workflows                                                                                                                         |
| `bioetl_audit_query_duration_seconds`          | Histogram | `layer_filter,status`                       | latency of audit inspection/query workflows                                                                                                                                   |

DQ anomaly timing semantics:

- `DataQualityService` вычисляет canonical DQ timestamp из того же
  application-owned freshness / ingestion anchor, который публикуется как
  `bioetl_data_freshness_seconds`
- этот timestamp MUST прокидываться в `DQMonitorPort.check_quality(...)` и
  `DQMonitorPort.update_baseline_from_metrics(...)`
- z-score / threshold anomaly timestamps therefore reflect the run anchor used
  by the application runtime, not a monitor-local wall clock

Guardrail для новых метрик control-plane/traceability:

- не использовать `run_id`, `manifest_id`, filesystem paths, `batch_id` и другие
  high-cardinality идентификаторы как Prometheus labels;
- агрегировать по `pipeline`, `run_type`, `event_type`, `layer`, `status`,
  `disposition`, а детализацию по конкретному запуску получать через
  `run-manifest show` и sidecar/control-plane артефакты.
- adaptive-memory metric families must stay bounded as well; `decision_index`,
  `record_index`, old/new batch sizes, host memory totals, RSS, and checkpoint
  payload details belong in checkpoint metadata, run ledger diagnostics, or
  trace events/attributes, not in Prometheus labels.
- stage-model and invariant metric families MUST stay bounded as well;
  unresolved counts may surface in gauges/counters, but `run_id`, `manifest_id`,
  raw batch identifiers, content hashes, and per-record forensic anchors must
  stay in control-plane artifacts, logs, or traces.
- provider health-check latency MUST use `_seconds` families only; `_ms`
  latency families для provider health-check path считаются legacy и не должны
  добавляться в новые dashboards, alerts или runtime emission paths
- audit traceability metric families MUST stay bounded as well; `run_id`,
  `table_name`, filesystem paths, and record identifiers belong in audit files,
  logs, or trace attributes, not in Prometheus labels

Новый `bioetl-control-plane-v1` dashboard собирает агрегаты manifest write
failures, ledger append failures, checkpoint compatibility и read failures, а
alert `BioETLControlPlaneReadFailureRate` (см. `docs/05-operations/runbooks/observability-checklist.md`)
визуализирует процент failed reads для каждого store/operation. Это панель
является первичной точкой диагностики control-plane regressions.

Recording rules трактуют любое ненулевое значение
`bioetl_manifest_ledger_integrity_ratio{integrity_type="inconsistent"}` как
fail-closed CRIT (`2`) одновременно в manifest/ledger failure и replay-safety
проекциях. Telemetry-completeness требует обе bounded series каждой новой
семьи; наличие только одной category series остаётся `UNKNOWN`, а не zero.

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
- NoOp и real adapter возвращают единый span surface:
  `set_attribute`, `add_event`, `record_exception` и context-manager lifecycle
- `OpenTelemetryTracer` владеет `TracerProvider` локально и не заменяет
  process-global provider при повторной или nested инициализации
- Exporter:
  - OTLP exporter при установленном OTLP пакете
  - fallback: Console exporter
  - для локальных OTLP endpoints (`localhost`, `127.0.0.1`, `host.docker.internal`,
    `tempo`) insecure/plaintext включается автоматически, если explicit
    `OTEL_EXPORTER_OTLP_INSECURE` override не задан

Текущее состояние:

- Спаны создаются на pipeline, composite lifecycle и HTTP-операциях
- Adaptive-memory decisions публикуются как bounded
  `bioetl.memory.decision` span events; tracing ON/OFF не меняет B/S/G counts
  или terminal execution status
- `CompositeLifecycleObserverService` использует sanctioned `TracingPort` seam
  для composite runtime lifecycle и создаёт bounded spans:
  - `pipeline.composite:<pipeline>`
  - `pipeline.composite:<pipeline>.<phase>`
- `postrun.run` дополнительно декомпозирован на nested spans:
  `postrun.compaction`, `postrun.dq_evaluation`, `postrun.dq_reports`,
  `postrun.vacuum`, `postrun.final_metadata`
- При включённом tracing composite lifecycle также инкрементит
  `bioetl_traced_runs_total` через injected `MetricsPort`; logger-only
  composite tracing path не считается canonical
- `logging_config.py` автоматически добавляет `trace_id` и `span_id` в structlog-записи,
  если в текущем контексте есть активный OTel span
- При отключённом tracing или отсутствии активного span лог-схема деградирует
  безопасно: поля `trace_id`/`span_id` просто не добавляются

## 4.1 Operator-facing diagnostics surface

Operator diagnostics не ограничиваются только `health` и metrics server.
Канонический public seam для observability-related bootstrap и diagnostics —
`bioetl.composition.observability_api`.

`bioetl.composition.observability_api` экспортирует единый diagnostics bundle и
service getters:

- `get_audit_service()`
- `get_health_service()`
- `get_checkpoint_service()`
- `get_metrics_service()`
- `get_metrics_operator_profile()`
- `get_observability_workflow_service()`
- `get_quarantine_service()`
- `get_run_manifest_service()`
- `get_lineage_service()`
- `get_observability_diagnostics_bundle()`

Это keeps-one-place discovery contract для public callers, при этом реальное
создание зависимостей остаётся в composition layer.

Для multi-step operator workflows каноническим application-level seam является
`ObservabilityWorkflowService`:

- `inspect_audit_run(run_id, limit=...)`
- `inspect_checkpoint_workflow(pipeline_name, run_id=..., audit_limit=...)`

Эти helpers агрегируют audit entries, checkpoint inspection и best-effort
run-manifest context, не перенося orchestration в CLI или interface layer.

CLI surface должен оставаться thin adapter над этим seam. Канонические
operator-facing команды:

- `bioetl diagnostics guide`
- `bioetl diagnostics metrics [--json]`
- `bioetl diagnostics health [--json]`
- `bioetl checkpoint audit-run --run-id ... [--limit ...] [--format text|json|yaml]`
- `bioetl checkpoint inspect --pipeline ... [--run-id ...] [--audit-limit ...] [--format text|json|yaml]`

`bioetl diagnostics metrics` является canonical operator summary для
metrics/admin behavior:

- metrics HTTP server startup остаётся auto-managed during pipeline runs when
  metrics are enabled;
- current metrics server status/config and Pushgateway publication mode should
  be discovered through `get_metrics_operator_profile()` /
  `bioetl diagnostics metrics`, not by reading composition helpers directly;
- Pushgateway publication остаётся best-effort on run completion, uses
  replace-style bounded aggregate snapshots (`push_to_gateway`), supports
  cleanup through `delete_metrics_from_gateway` / `delete_from_gateway`, and
  does not require a separate operator command for normal execution.
- Pushgateway grouping labels are limited to `pipeline` and `run_type`;
  `run_id`, `record_id`, `payload_hash`, raw paths/URLs, and other forensic
  anchors remain in manifest/ledger/CLI/explorer surfaces.

Selected operator/admin service seams also emit bounded tracing spans through
`TracingPort` when tracing is enabled:

- `MetricsService.start`, `MetricsService.get_status`, `MetricsService.push_to_gateway`,
  `MetricsService.delete_from_gateway`
- `quarantine.inspect` (`QuarantineService.inspect`),
  `quarantine.get_stats` (`QuarantineService.get_stats`),
  `quarantine.replay` (`QuarantineService.replay`),
  `quarantine.mark_reprocessed`,
  `quarantine.purge` (`QuarantineService.purge`),
  `quarantine.update_status` (`QuarantineService.update_status`)
- `ObservabilityWorkflowService.inspect_audit_run`, `ObservabilityWorkflowService.inspect_checkpoint_workflow`
- `FileAuditAdapter.log_write`, `FileAuditAdapter.get_entries`, `FileAuditAdapter.aclose`

Intentional non-goals for now:

- per-record quarantine explorer/detail lookup flows are not traced
- filtered quarantine explorer workflows remain metric/log-only:
  `list_filtered_records`, `get_filtered_record`, `get_filtered_stats`,
  `get_filtered_filter_options`
- CLI commands themselves do not create spans directly; tracing stays in application services

## 5. Provider Rate-Limit Baseline (as configured)

Значения ниже берутся из `configs/providers/*.yaml` и отражают **текущую конфигурацию репозитория**, не внешние SLA провайдеров.

| Provider        | Base RPS | Burst | API-key override |
| --------------- | -------: | ----: | ---------------- |
| chembl          |        3 |    10 | -                |
| pubchem         |      5.0 |    10 | -                |
| pubmed          |      3.0 |     5 | `10 / 20`        |
| crossref        |       50 |   100 | polite pool flag |
| openalex        |       10 |    20 | API key / credit model |
| semanticscholar |      0.1 |     1 | `1.0 / 5`        |
| uniprot         |     10.0 |    20 | `100 / 200`      |

## 6. Alert Threshold Baseline

Рекомендуемая минимальная таблица (runbook links локальные):

Принцип shipped baseline: Prometheus rules должны быть fleet-wide и опираться
на `pipeline` / `provider` labels, а не на отдельные per-pipeline packs вроде
`chembl_assay`-only alert groups.

| Metric                                                                         | Condition                                                                                                                                                                                           | Severity | Runbook                                                        |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------- |
| `bioetl_pipeline_runs_total{status="failed"}`                                  | `increase(...) > 0` за `15m`                                                                                                                                                                        | P1       | `docs/05-operations/runbooks/pipeline-failure-critical.md`     |
| `bioetl_control_plane_manifest_writes_total{status="failed"}`                  | `increase(...) > 0` за `15m`                                                                                                                                                                        | P1       | `docs/05-operations/runbooks/run-manifest-inspection.md`       |
| `bioetl_control_plane_ledger_appends_total{status="failed"}`                   | `increase(...) > 0` за `15m`                                                                                                                                                                        | P1       | `docs/05-operations/runbooks/run-manifest-inspection.md`       |
| `bioetl_manifest_ledger_integrity_ratio{integrity_type="inconsistent"}`        | `> 0` на последнем bounded reconciliation refresh                                                                                                                                                    | P0       | `docs/05-operations/runbooks/run-manifest-inspection.md`       |
| `bioetl_pipeline_health_check_passed`                                          | `== 0` за `5m`                                                                                                                                                                                      | P1       | `docs/05-operations/runbooks/pipeline-failure-critical.md`     |
| `bioetl_provider_health_status`                                                | `== 0` за `5m`                                                                                                                                                                                      | P2       | `docs/05-operations/runbooks/incident-response.md`             |
| `bioetl_circuit_breaker_state`                                                 | `== 2` за `5m`                                                                                                                                                                                      | P2       | `docs/05-operations/runbooks/incident-response.md`             |
| `bioetl_dq_validation_score`                                                   | `< 0.80` на запуск                                                                                                                                                                                  | P2       | `docs/05-operations/runbooks/pipeline-failure-dq.md`           |
| `bioetl_dq_records_quarantined_total`                                          | `>5%` и `<=20%` за `30m` при `bronze>=20`                                                                                                                                                           | P2       | `docs/05-operations/runbooks/pipeline-failure-dq.md`      |
| `bioetl_dq_records_quarantined_total`                                          | `>20%` за `15m` при `bronze>=20`                                                                                                                                                                    | P1       | `docs/05-operations/runbooks/pipeline-failure-dq.md`      |
| `time() - bioetl_data_freshness_seconds`                                       | `>24h` и `<=72h`                                                                                                                                                                                    | P2       | `docs/05-operations/runbooks/pipeline-failure-dq.md`      |
| `time() - bioetl_data_freshness_seconds`                                       | `>72h`                                                                                                                                                                                              | P1       | `docs/05-operations/runbooks/pipeline-failure-dq.md`      |
| `bioetl_checkpoint_compatibility_events_total{disposition=~".*_incompatible"}` | `increase(...) > 0` за `30m`                                                                                                                                                                        | P2       | `docs/05-operations/runbooks/checkpoint-debugging.md`          |
| `bioetl_lineage_fragments_emitted_total{status="failed"}`                      | `increase(...) > 0` за `15m`                                                                                                                                                                        | P2       | `docs/05-operations/runbooks/traceability-signal-ownership.md` |
| `bioetl_lineage_refs_missing_total`                                            | `increase(...) > 0` за `15m`                                                                                                                                                                        | P2       | `docs/05-operations/runbooks/traceability-signal-ownership.md` |
| `bioetl_control_plane_reads_total{status="failed"}`                            | `(sum by (store, operation) (increase(bioetl_control_plane_reads_total{status="failed"}[30m])) / clamp_min(sum by (store, operation) (increase(bioetl_control_plane_reads_total[30m])), 1)) > 0.05` | P2       | `docs/05-operations/runbooks/observability-checklist.md`       |
| `bioetl_data_source_retry_exhausted_total`                                     | `1-2` exhaustions за `1h`                                                                                                                                                                           | P2       | `docs/05-operations/runbooks/incident-response.md`             |
| `bioetl_data_source_retry_exhausted_total`                                     | `>=3` exhaustions за `1h`                                                                                                                                                                           | P1       | `docs/05-operations/runbooks/incident-response.md`             |
| `bioetl_rate_limiter_wait_seconds`                                             | `histogram_quantile(0.95, ...) > 1` за `10m`                                                                                                                                                        | P3       | `docs/05-operations/runbooks/observability-checklist.md`       |

`bioetl_composite_source_selection_total` intentionally remains a dashboard/reporting
signal rather than a shipped Prometheus alert baseline. It tracks bounded
composite arbitration activity (`decision_type`, `selected_source`) but does
not, by itself, indicate an incident condition.

`bioetl_data_freshness_seconds` currently reflects the ingestion anchor carried
into successful runtime evaluation (currently `PipelineContext.started_at`),
not a separate postrun wall-clock publication timestamp.

## 7. Error Taxonomy (domain canonical)

Коды ошибок из `ErrorType` (`src/bioetl/domain/types/enums.py`):

- Critical: `AUTH_FAILURE`, `DB_UNAVAILABLE`, `SCHEMA_MISMATCH_GOLD`, `SCHEMA_EVOLUTION`, `LOCK_LOST`
- Recoverable: `RATE_LIMIT`, `TIMEOUT`, `NETWORK_ERROR`
- Data quality: `SCHEMA_VIOLATION`, `INVALID_DATA`, `MISSING_REQUIRED_FIELD`, `DATA_QUALITY`

## 8. Known Drifts and Required Follow-ups

- На момент `2026-04-12` явных drift'ов внутри канонического observability
  contract pack (`docs/02-architecture/observability-layers.md`,
  `docs/04-reference/contracts/observability.md`,
  `docs/05-operations/01-monitoring-guide.md`,
  `docs/05-operations/sli-slo-baseline.md`) не зафиксировано.
- Дополнительные runbook/dashboard drift'ы должны отслеживаться обычным
  documentation-audit потоком, а не оставаться неявными внутри core contract
  doc.

## 9. Definition of Done for observability doc sync

- Все спецификации/чеклисты используют `bioetl_...` naming
- Во всех docs используется `run_id` (не `run-id`)
- Mapping для `provider_health_status` совпадает с `HealthStatus.to_metric_value()`
- Поле времени в лог-схеме описано как `timestamp` (или явно как dual-mode `timestamp/ts`)
- Алерты используют реальные `status` (`failed`, `success`, `shutdown`) из runtime
- Log/trace correlation через `trace_id` и `span_id` соответствует runtime processor chain
