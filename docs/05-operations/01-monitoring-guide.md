______________________________________________________________________

Version: 1.0.4
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-10'

______________________________________________________________________

# 05.01 Руководство по мониторингу (Monitoring Guide)

*Reference: [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Мониторинг ориентирован на локальный процесс BioETL и локальные endpoint'ы метрик.

BioETL использует стек **Prometheus + Grafana** для обеспечения полной наблюдаемости за процессом сбора и трансформации данных. Данный документ описывает структуру системы, доступные дашборды и способы интерпретации данных.

`Observability Checklist` complements this guide: use this page for observability
surface interpretation and shipped alert semantics, and use
[runbooks/observability-checklist.md](runbooks/observability-checklist.md) for
operator validation and incident-readiness checks.

`SLI/SLO Baseline` complements both documents: use
[sli-slo-baseline.md](sli-slo-baseline.md) for numeric operational objectives,
target windows, and alert-to-SLI mapping.

## 0. Канонический operator workflow

Используйте observability surface в таком порядке:

1. `bioetl diagnostics guide` — discovery entrypoint для supported commands.
1. `bioetl diagnostics metrics [--json]` — текущий metrics/admin profile:
   endpoint, running/stopped status, tracing/audit flags и Pushgateway mode.
1. `bioetl diagnostics health [--json]` — provider health summary.
1. `bioetl diagnostics run --run-id <run-id>` или
   `bioetl diagnostics checkpoint --pipeline <pipeline>` — workflow-level
   расследование run/checkpoint state.
1. `python -m scripts.engineering.qa report-observability-metric-inventory --json` —
   reconciliation surface между runtime emitters, docs и Prometheus rules.
1. Сравните inventory output с
   `grafana/prometheus-rules/bioetl_observability.yml` и shipped dashboard JSON
   до того, как трактовать missing panels как runtime outage.

Важно:

- metrics HTTP server startup остаётся auto-managed during normal pipeline runs;
- Pushgateway publication остаётся best-effort on run completion;
- `bioetl diagnostics metrics` — canonical operator summary для этих
  auto-managed observability behaviors.

## 1. Архитектура наблюдаемости

Система мониторинга построена на принципе "Pull":

1. **BioETL App**: При запуске пайплайна поднимает временный HTTP-сервер (порт 8000), экспортирующий метрики в формате OpenMetrics.
1. **Prometheus**: Регулярно собирает (scrape) метрики из приложения и сохраняет их в базе данных временных рядов (TSDB).
1. **Grafana**: Выступает в роли интерфейса визуализации, подключаясь к Prometheus как к источнику данных.

Для короткоживущих запусков BioETL дополнительно использует best-effort
Pushgateway publication на завершении run. Это позволяет сохранить итоговые
метрики после завершения процесса и уменьшает зависимость operator-поверхностей
от удачного scrape-окна.

Для Loki в shipped конфигурации уже включён `limits_config.volume_enabled: true`
в файле `grafana/loki-config.yml`.
Это полезно для live validation и Explore-side log volume inspection, даже если
сами Prometheus dashboards не зависят от этой опции напрямую.

## 2. Использование Дашбордов

Все дашборды в BioETL v5.1+ поддерживают **динамическую фильтрацию**.

### Фильтрация и Изоляция данных

В верхней части каждого дашборда расположены выпадающие списки:

- **1. Overview / 2. Runtime / 4. Data Quality**: `$pipeline`, `$run_type`
- **3. Provider Health**: `$provider`
- **5. Silver Reject Explorer**: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash`

> **Важно**: для `1-4` dashboard допустим общий scope (`All`), но
> `5. Silver Reject Explorer` требует **scoped pipeline** (single-select, без
> `All`), иначе backend quarantine API возвращает fail-closed ошибку.

### Основные Дашборды

#### 1. 1. Overview

Центральный дашборд для контроля за выполнением пайплайнов.

- **Processing Volume by Stage**: stage-volume trend за активное окно Grafana.
- **Stage Distribution in Range / Pipeline Distribution in Range**: selected-range срезы распределения.
- **Overall Yield (Selected Range)**: `gold[$__range] / clamp-min(bronze[$__range], 1)`.
- **Control Plane & Lineage**: отдельная строка для `Manifest Writes (24h)`,
  `Ledger Appends (24h)`, `Checkpoint Incompatibilities (24h)`,
  `Lineage Refs Missing (24h)` и `Global Control-plane Lookup` сигналов.
- **Composite Source Selections (24h)**: informational counter по
  `bioetl_composite_source_selection_total`, который показывает bounded
  composite arbitration activity в выбранном `$pipeline`. Это не alert-state
  signal, а operator context для случаев, когда composite path неожиданно
  меняет источник данных или перестаёт выбирать expected source.
- **Global Control-plane Lookup Failures (24h) / Global Control-plane Lookup p95 (1h)**:
  показывают, можно ли читать manifest/ledger/lineage обратно и насколько
  дорогими становятся lookup paths во время расследований. Эти сигналы сейчас
  global по стеку и не фильтруются по `$pipeline`.
- **Lineage Fragment Outcomes (1h)**: тренд публикации lineage fragments по
  `layer/status` без использования high-cardinality labels.
- **Drilldown**: dashboard links `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)`
  и data links у `Processing Volume by Stage` переводят оператора в Grafana Explore с тем
  же временным окном. Tempo handoff уже предфильтрован по текущим `$pipeline/$run_type`.

#### 2. 2. Runtime

Смешанный runtime/ops surface для triage log hygiene и alert-condition сигналов.
Dashboard теперь намеренно остаётся **Prometheus-first**: базовые summary,
adaptive-memory и alert-condition панели должны быть usable даже без Loki/Tempo,
а tracing-backed log hygiene вынесен в collapsed row `Tracing-only Log Hygiene
(requires optional tracing profile)`.

- **Warnings / Unstructured Logs**: range-based count structured warning logs и unstructured rows по текущему `$pipeline`.
  Эти Loki-панели живут внутри collapsed tracing-only row и не считаются частью
  обязательного base layout для режима без `tracing` profile.

- **Pipeline / DQ / Control-plane / Provider / Freshness Alert Conditions**: Prometheus-backed stat panels, которые отражают те же условия, что и alert rules, но не притворяются real alert-state engine.

- `Pipeline / DQ / Control-plane / Provider / Freshness Alert Conditions` теперь считают
  количество активных семейств условий, а не сырые суммы event counters.

- **Top Warning Events**: быстрый range-based срез наиболее частых warning events.

- **Log Hygiene Trend**: короткий timeseries-тренд warnings vs unstructured rows через `$__interval`.

- **Drilldown**: dashboard links `Back to Overview`, `Control Plane v1`,
  `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)` и data links у `Log Hygiene Trend` ведут в Explore с тем же временным окном.
  Panels `Control-plane Alert Conditions`, `No-Records Processed Runs` и
  `Replay Not Reconstructable` дополнительно дают прямой handoff в
  `Control Plane v1`, чтобы checkpoint/replay/lineage incidents не требовали
  ручного поиска следующего dashboard. Для Tempo runtime surface используется
  TraceQL filter по текущим `$pipeline/$run_type`, а не пустой search.

- **Tracing Mode Note**: верхняя note-панель прямо под `Runtime Scope`
  напоминает, что без включённого `tracing` profile оператор должен опираться
  на Prometheus-backed surfaces (`Overview`, `Control Plane`, `Data Quality`) и
  разворачивать tracing-only row только в окружениях с реальными Loki/Tempo
  datasource.

- **DQ Context Failures (24h) / DQ Reports Skipped (24h) / DQ Reports Generated (24h)**:
  lifecycle counters для DQ reporting. Используйте их, когда нужно быстро
  понять, не сломалась ли сборка DQ context, отчёты системно пропускаются или
  наоборот стабильно доходят до успешной генерации.

- **Memory Pressure Events / Batch Resize Events / Fallback Monitor Decisions / Memory Pressure Active**:
  adaptive-memory triage surface. Эти панели помогают отделить реальное memory
  pressure от recovery/fallback-mode решений и быстро увидеть, не ушёл ли
  runtime в `resource` / `estimate` path вместо штатного monitor mode.

- **Trace-enabled Runs (24h)**: показывает, были ли за окно запуски с реальным
  tracing path. Если здесь `0`, пустой Tempo для выбранного `$pipeline/$run_type`
  ожидаем. Если здесь значение больше нуля, а `Explore Traces (Tempo, tracing profile)` пуст,
  это уже сигнал разбирать exporter / flush / ingestion path.

- **Pipeline Alert Conditions (15m)**: fleet-wide срез по трем главным runtime
  рискам: preflight `data_source`, `infrastructure_validated` и
  `pipeline_runs_total{status="failed"}`. Если панель активна, расследование
  стоит начинать с `pipeline-failure-critical.md`, а не только с provider/DQ path.
  Начиная с текущего baseline dashboard читает recording-rule series
  `bioetl_runtime_alert_condition_*`, чтобы не дублировать тяжёлую alert
  PromQL-логику прямо в JSON-панелях.

- **Global Control-plane Lookup Outcomes (1h) / Global Control-plane Lookup p95 (1h)**:
  runtime-срез по success/miss/failed для manifest, ledger и lineage lookup
  paths. Эти панели особенно полезны, когда write-side выглядит здоровым, но
  follow-up investigation или lineage drilldown начинают терять данные. Они не
  привязаны к `$pipeline`, потому что underlying control-plane read metrics не
  несут pipeline label.

- **Control-plane aggregate view**: используйте `bioetl-control-plane-v1` для
  мониторинга aggregated manifest write failures, ledger append failures,
  checkpoint compatibility и read failure ratio. Новое правило
  `BioETLControlPlaneReadFailureRate` (см. `docs/05-operations/runbooks/observability-checklist.md`)
  срабатывает, если доля failed reads по store/operation превышает 5% за 30m.

#### 3. 3. Provider Health

Технический мониторинг состояния внешних API (ChEMBL, UniProt и др.).

- **Health Check Latency by Provider (p95)**: тренд латентности провайдеров.
- **Healthy Checks / Degraded Checks / Health Checks Total**: разделяют completed probes по outcome и не маскируют `DEGRADED` как success.
- **Failure & Degraded Trend by Provider**: показывает устойчивость деградации по каждому provider в выбранном time range.
- **Provider Failure Share (Selected Range)**: ранжирует providers по доле failed probes внутри активного scope.
- **Retries Exhausted by Provider / Operation** и **Retries Exhausted Trend by Provider / Operation**:
  показывают, где и насколько часто исчерпываются retries (`bioetl_data_source_retry_exhausted_total`).
- **Per-provider gauge (102)**: повторяемая p95-панель по `$provider`.
- **Drilldown**: dashboard links `Back to Overview`, `2. Runtime`, `Explore Logs (Loki, tracing profile)` /
  `Explore Traces (Tempo, tracing profile)` и data links у latency-панели открывают correlation path. Для Loki shipped
  baseline стартует с общего `{job="bioetl"}` stream, а дополнительное
  сужение по `provider` оператор делает уже в Explore. Tempo handoff здесь сразу
  использует `span."bioetl.provider"` для текущего `$provider`.

#### 4. 4. Data Quality

Сфокусирован на чистоте данных и аномалиях.

- **Data Quality Score (Volume-weighted)**: volume-aware gauge на базе
  `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`.
- **Worst-Entity DQ Score**: быстрый worst-case сигнал по сущностям в выбранном pipeline scope.
- **Quarantine / Soft Threshold / Validation Failures**: контроль деградаций по окнам времени.
- **Anomalies / DQ p95 / Data Freshness**: детальные DQ-сигналы. Текущий
  freshness gauge отражает ingestion anchor текущего успешного запуска
  (сейчас это `PipelineContext.started_at`, который также прокидывается в
  `_ingestion_ts` runtime writes); lag интерпретируется как
  `time() - bioetl_data_freshness_seconds`.
- **Drilldown**: dashboard links `Back to Overview`, `Control Plane v1`,
  `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)`
  и data links у `Data Flow in Range: Bronze -> Silver -> Gold` переводят расследование
  DQ incidents и freshness lag в Grafana Explore с тем же временным окном.
  Для replay/checkpoint traceability panel `Data Flow in Range: Bronze -> Silver -> Gold`,
  а также `Lineage Refs Missing` и `Gold Strict Validation Failures`, теперь
  дают прямой handoff в `Control Plane v1`.
  Tempo handoff уже ограничен текущими `$pipeline/$run_type`.

#### 5. 5. Silver Reject Explorer

Record-level dashboard для `FILTERED_OUT_SILVER` записей (quarantine-backed, read-only datasource).

- **Filtered Records Table**: полный список отфильтрованных записей с server-side filtering/pagination.
- **Selected Record Details**: exact reject context по выбранному `payload_hash`.
- **Top Reject Reasons / Fields / Signatures**: агрегаты в том же scoped контексте.
- **Datasource**: `Quarantine Explorer` (JSON/Infinity), не Prometheus.
- **Drilldown**: links `Back to Overview`, `Back to Data Quality`, `Open Logs`, `Open Traces` и row-level link в CLI-команду.

#### Quarantine operator metrics

CLI and bootstrap-backed quarantine operations now emit bounded operator metrics:

- `bioetl_quarantine_operator_operations_total`
- `bioetl_quarantine_operator_duration_seconds`

Use them when investigating replay/purge/update/inspect regressions that do not
surface clearly through record-level reject exploration.

#### Checkpoint operator metrics

Checkpoint admin workflows emit a separate bounded operator surface:

- `bioetl_checkpoint_operator_operations_total`
- `bioetl_checkpoint_operator_duration_seconds`

Use them when investigating `bioetl checkpoint list|get|delete` regressions or
operator-facing checkpoint store latency outside ordinary runtime resume paths.

#### Silver Filter Rejects Handoff

- Используйте `1. Overview` или `2. Runtime` как summary surface, чтобы
  подтвердить spike по `Silver Filter Rejects` в активном Grafana time range.
- После подтверждения переходите в `4. Data Quality`, где
  `Top Silver Reject Reasons` и `Top Silver Reject Fields` дают bounded cause
  summary без raw quarantine text.
- Для row-level browsing переходите в `5. Silver Reject Explorer`.
- CLI остаётся execution surface для replay/resolve:
  `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --run-id <run-id> --limit 200` и
  `bioetl quarantine resolve --pipeline <pipeline> --payload-hash <payload-hash> --status IGNORED`.

## 3. Alert-backed сигналы

Для shipped observability baseline дополнительно отслеживаются:

- **Control plane / traceability**
  - `BioETLControlPlaneManifestWriteFailed` -> `run-manifest-inspection.md`
  - `BioETLRunLedgerAppendFailed` -> `run-manifest-inspection.md`
  - `BioETLCheckpointCompatibilityBlocked` -> `checkpoint-debugging.md`
  - `BioETLLineageFragmentPersistenceFailed` -> `traceability-signal-ownership.md`
  - `BioETLLineageRefsMissing` -> `traceability-signal-ownership.md`
- **Pipeline runtime**
  - `BioETLPipelinePreflightDataSourceFailed` -> `pipeline-failure-critical.md`
  - `BioETLPipelineInfrastructureValidationFailed` -> `pipeline-failure-critical.md`
  - `BioETLPipelineRunFailed` -> `pipeline-failure-critical.md`
- **DQ / freshness**
  - `BioETLDQSoftThresholdExceeded` -> `dq-failure-investigation.md`
  - `BioETLDQQuarantineRateHigh` / `BioETLDQQuarantineRateCritical` -> `dq-failure-investigation.md`
    (`5-20%` warning / `>20%` critical, только при `bronze>=20`)
  - `BioETLDQValidationFailuresCritical` -> `dq-failure-investigation.md`
  - `BioETLDQCriticalAnomaliesDetected` -> `dq-failure-investigation.md`
  - `BioETLSilverValidationFailuresDetected` -> `dq-failure-investigation.md`
    (driven by `bioetl_silver_validation_failures_total`, which increments on
    canonical failed Silver Pandera validation outcomes with bounded
    `table/pipeline` labels)
  - `BioETLDataFreshnessLagHigh` / `BioETLDataFreshnessLagCritical` -> `dq-failure-investigation.md`
    (`24-72h` warning / `>72h` critical; lag считается как `time() - bioetl_data_freshness_seconds`)
- **Provider health**
  - `BioETLProviderHealthCheckFailuresDetected` -> `incident-response.md`
  - `BioETLProviderFailureRateHigh` -> `incident-response.md`
  - `BioETLProviderRetriesExhausted` / `BioETLProviderRetriesExhaustedPersistent` -> `incident-response.md`
    (`1-2` exhaustions per `1h` warning / `>=3` critical)

`2. Runtime` показывает эти сигналы как **alert conditions**, а не как
гарантированное состояние rule engine. Это сознательно: в shipped stack rules
живут в Prometheus, но отдельный alert-state datasource в Grafana не
provisioned.

### Threshold smoke baseline

Для быстрых локальных проверок держим сценарный smoke baseline в
`tests/integration/test_prometheus_rules_config.py`.

Покрываемые границы:

- quarantine-rate: `<20 bronze`, `5%`, `5.1%`, `20%`, `20.1%`
- freshness: `24h`, `24h+1s`, `72h`, `72h+1s`
- provider retry exhaustion: `0`, `1`, `2`, `3` событий за `1h`

Быстрый прогон:

```bash
uv run python -m pytest -q tests/integration/test_prometheus_rules_config.py
```

## 4. Гарантии качества мониторинга

Все конфигурации дашбордов проходят автоматическую проверку (**Contract Testing**). Это гарантирует, что:

1. Дашборды используют только реально существующие в коде метрики.
1. На всех панелях настроены правильные единицы измерения (nM, bytes, sec).
1. Переменные фильтрации `$pipeline`, `$run_type` и `$provider` работают корректно.

Подробнее см. в документации по тестированию наблюдаемости.

## 5. Что делать если... (Runbook Lite)

- **График "Error Rate" покраснел**: Используйте `structlog` для получения деталей исключений.
- **Вырос `Silver Filter Rejects`**:
  1. Подтвердите spike в `1. Overview` или `2. Runtime`.
  1. Перейдите в `4. Data Quality` и проверьте `Top Silver Reject Reasons` /
     `Top Silver Reject Fields`.
  1. Перейдите в `5. Silver Reject Explorer` для списка записей и detail по `payload_hash`.
  1. Если нужны action-операции, используйте quarantine CLI (`inspect/resolve/replay`).
- **`5. Silver Reject Explorer` показывает `No data` во всех панелях**:
  1. Проверьте, что backend доступен и `pipeline` явно задан:
     `curl "http://127.0.0.1:8081/ops/quarantine/filter-options?pipeline=<pipeline_name>"`.
  1. Убедитесь, что в dashboard выбран конкретный `$pipeline` (single-select),
     а не общий scope.
  1. Проверьте, что сервер поднят с внешним bind для Grafana container:
     `bioetl health server --host 0.0.0.0 --port 8081`.
  1. Проверьте наличие Infinity plugin и datasource:
     `curl -u admin:<password> http://localhost:3000/api/datasources` должен содержать `Quarantine Explorer`,
     а `curl -u admin:<password> http://localhost:3000/api/plugins/yesoreyeram-infinity-datasource/settings`
     должен возвращать `200`.
  1. Для Grafana 12+ используйте `GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource`
     (legacy `GF_INSTALL_PLUGINS` оставляем только для обратной совместимости).
  1. Убедитесь, что Grafana datasource `Quarantine Explorer` указывает на
     `http://host.docker.internal:8081` (или ваш override `BIOETL_QUARANTINE_EXPLORER_URL`).
  1. Если используется Linux Docker engine, проверьте что у Grafana есть
     `host.docker.internal` (`extra_hosts: host-gateway`).
- **Дашборд пустой**:
  1. Проверьте, что пайплайн-процесс запущен и не завершился с ошибкой.
  1. Убедитесь, что пайплайн запущен с метриками (`BIOETL_METRICS_ENABLED=true`).
  1. Проверьте доступность endpoint метрик на порту 8000 (`/metrics`).
- **Loki drilldown не находит событие**:
  1. Сначала проверьте, что общий запрос `{job="bioetl"}` вообще возвращает строки.
  1. После этого сузьте запрос вручную по `pipeline`, `provider` или `stage` уже в Explore.
  1. Не полагайтесь на `$pipeline/$provider` interpolation внутри encoded Explore payload.
- **Метрики показывают UNHEALTHY для storage**: Проверьте права доступа к папкам `data/`.
- **Control-plane сигналы стали красными**:
  1. Запустите `bioetl run-manifest show <run-id|manifest-id> --format json`.
  1. Проверьте `diagnostics.alert_signals`, `artifact_refs`,
     `artifact_refs[*].artifact_id`, `lineage_fragment_ids`,
     `missing_artifact_links`.
  1. Если проблема связана с resume, откройте runbook
     `checkpoint-debugging.md`.

## 6. Ссылки

- [Архитектурное решение ADR-017 (Observability)](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [Правила именования метрик (RULES.md)](../00-project/RULES.md)
