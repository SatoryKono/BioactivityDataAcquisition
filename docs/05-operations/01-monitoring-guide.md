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

- **0. Control Plane / 1. Overview**: `$pipeline`, `$run_type`
- **2. Runtime / 4. Data Quality**: `$pipeline`, `$run_type`, `$stage`
- **3. Provider Health**: `$provider`, `$adapter`
- **Silver Reject Explorer**: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash`
- **5. Workflow**: `$workflow`, `$status`

> **Важно**: `$pipeline` и `$provider` single-select на всех shipped
> dashboards, `All` запрещён. Если контекста нет, используется explicit
> fallback `unknown`. `$run_type` является include-all scope: если контекста
> запуска нет, используйте `Run Type=All`, а не `unknown`. Переход в `3. Provider Health` из pipeline-scoped
> dashboards мапит `$pipeline` в `$provider` и сохраняет hidden
> `$pipeline_context` для обратного перехода.

### Основные Дашборды

#### 1. Overview

L0 дашборд для одного operator question: что сейчас broken/degraded в BioETL и
куда drill down первым.

- **Answer row**: `System Status`, `Next Action`, `Failed Runs in Range`,
  `Recent Activity`, `Worst Backlog Stage`, `Worst Lag Stage`. `OK` requires
  recent activity; no samples/no denominator stays `UNKNOWN`, not green.
- **Flow evidence**: `Flow Balance` replaces the old yield gauge and shows
  Bronze denominator, Gold output, filtered/quarantined counts and unaccounted
  loss. `Backlog Causality` places backlog, lag and throughput together for the
  runtime invariant `backlog(t+1) = backlog(t) + ingestion - output`.
- **Trend row**: `Processing Volume by Stage`, `Pipeline Run Outcomes`,
  `Stage Backlog Trend`, `Stage Lag Trend`; это context для L0 решения, а не
  forensic/debugging surface.
- **Subsystem routing**: `Runtime Status`, `Data Quality Status`,
  `Control Plane Status`, `Provider Status`, `Workflow Status` показывают
  status + reason + next dashboard вместо numeric handoff cards.
- **Failure summary**: только compact selected-range summaries по manifest /
  ledger, checkpoint, lineage и `Silver Rejects Count + Rate`. Distribution
  pie panels, standalone vanity yield/rate gauges и composite source-selection
  detail не входят в L0 flow.
- **Drilldown**: top-level шина содержит `0. Control Plane`, `2. Runtime`,
  `3. Provider Health`, `4. Data Quality`, `5. Workflow`. Explore links на
  Overview отсутствуют; Runtime/DQ/Control Plane links передают только
  target-scoped variables.

#### 2. 2. Runtime

`2. Runtime` теперь является **L2 diagnostic dashboard**. Его primary question:
где pipeline runtime теряет время, падает, копит backlog или даёт
warning/error conditions. Dashboard остаётся **Prometheus-first**:
answer row, latency/localization и handoff-панели usable без Loki/Tempo, а
tracing-backed log hygiene живёт в collapsed row
`Tracing-only Log Hygiene (requires optional tracing profile)`.

- **Top answer row**:
  `First Action`, `Monitor Runtime Current Status`, `Runtime Blockers`,
  `Inspect Top Runtime Blockers`.
  Это первый экран triage. Если здесь уже понятно, что runtime blocked,
  оператор не должен сначала прокручивать в logs/traces.

- **Localization row**:
  `Stage Backlog Trend`, `Records by Stage / Interval`,
  `Pipeline Phase Duration p50/p95/p99`,
  `Pipeline Duration p50/p95/p99`,
  `Errors by Stage / Error Code / Range`,
  `Records by Stage / Run Type / Range`.
  Эти панели отвечают на вопрос, в каком stage/phase runtime теряет время,
  поток записей или стабильность.

- **Handoff row**:
  `Pipeline Alert Conditions`, `DQ Alert Conditions`,
  `Control-plane Alert Conditions`, `GLOBAL Provider Alert Conditions`,
  `Freshness Alert Conditions`,
  `Shutdown Initiated by Reason / Interval`,
  `Shutdown Completed by Reason / Interval`.
  Это именно compact handoff surfaces, а не попытка дублировать DQ,
  Provider Health или Control Plane dashboards.

- **Logs/traces row**:
  `Warnings`, `Unstructured Logs`, `Top Warning Events`, `Log Hygiene Trend`
  остаются shipped, но спрятаны в collapsed tracing-only row. Если tracing
  profile выключен, оператор всё равно получает usable runtime triage без Loki
  и Tempo.

- **Drilldown contract**:
  top-level links `0. Control Plane`, `1. Overview`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow`, `Explore Logs`, `Explore Traces`.
  Panel-level dashboard handoffs запрещены, если target уже доступен в
  top-level шине. `run_id`, `payload_hash`, `record_id` в runtime dashboard
  запрещены.

- **Runbook routing**:
  `Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `DQ Alert Conditions` / `Freshness Alert Conditions` ->
  `dq-failure-investigation.md`,
  `Control-plane Alert Conditions` -> `run-manifest-inspection.md`,
  `GLOBAL Provider Alert Conditions` -> `incident-response.md`,
  `No-Records Runs / 30m` -> `checkpoint-debugging.md`.

- **Known missing metrics**:
  `Retry vs Failure` и `Batch Size Distribution` сознательно не показаны в
  runtime dashboard, потому что в shipped repo нет подтверждённой bounded
  runtime metric family для этих решений. Это отдельный instrumentation
  follow-up, а не повод выдумывать PromQL.

#### 3. 3. Provider Health

Технический мониторинг состояния внешних API (ChEMBL, UniProt и др.).

- **Current Provider Health Status**: table panel по
  `bioetl_provider_health_status{provider}` с явным mapping:
  `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`.
- **Track Health Check Latency by Provider (p95)**: selected-range тренд латентности провайдеров.
- **Monitor Healthy Checks (Selected Range) / Monitor Degraded Checks (Selected Range) / Track Health Checks Total (Selected Range)**: selected-range evidence по completed probes; эти панели не являются current-health source.
- **Failure & Degraded Trend by Provider**: показывает устойчивость деградации по каждому provider в выбранном time range.
- **Track Provider Failure Share (Selected Range)**: ранжирует providers по доле failed probes внутри активного scope.
- **Retries Exhausted by Provider / Operation** и **Retries Exhausted Trend by Provider / Operation**:
  показывают, где и насколько часто исчерпываются retries (`bioetl_data_source_retry_exhausted_total`).
- **Per-provider gauge (102)**: повторяемая p95-панель по `$provider`.
- Для provider/control-plane/runtime/DQ latency panels `No data` нужно читать
  как “в окне нет latency samples”, а не как нормализованный `0s`.
- **Drilldown**: dashboard links `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `4. Data Quality`, `5. Workflow`. Explore links на Provider
  Health отсутствуют; provider correlation идёт через top-level Runtime/DQ
  переходы и runbook links.

#### 4. 4. Data Quality

Сфокусирован на текущем DQ incident state и selected-range evidence.

- **First answer row**: `Monitor DQ Current Status`,
  `Monitor DQ Threshold State`, `Inspect DQ Current Reasons` и
  `First Action / Invalid Record Policy` отвечают, является ли DQ сейчас
  `OK`, `DEGRADED`, `FAILING` или `UNKNOWN`.
- **Data Quality Score (Volume-weighted)**: volume-aware gauge на базе
  `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`.
- **Worst-Entity DQ Score**: быстрый worst-case сигнал по сущностям в выбранном pipeline scope.
- **Quarantine / Soft Threshold / Validation Failures**: контроль деградаций по окнам времени.
- **Anomalies / DQ p95 / Data Freshness**: детальные DQ-сигналы. `Worst Data
  Freshness Lag (seconds)` теперь показывает самый stale entity в выбранном
  scope через `max(time() - bioetl_data_freshness_seconds)`, а
  `Latest Successful Data Timestamp` остаётся отдельным latest-success anchor.
  Это intentionally разные сигналы: latest success не должен маскировать worst
  freshness lag.
- **Drilldown**: dashboard links `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `5. Workflow`, `Silver Reject Explorer`,
  `Explore Logs`, `Explore Traces`. Panel-level dashboard handoffs запрещены:
  replay/checkpoint traceability открывается через `0. Control Plane` в
  top-level шине.
  Tempo handoff уже ограничен текущими `$pipeline/$run_type`.

#### Silver Reject Explorer

Record-level dashboard для `FILTERED_OUT_SILVER` записей (quarantine-backed, read-only datasource).

- **Filtered Records Table**: полный список отфильтрованных записей с server-side filtering/pagination.
- **Selected Record Details**: exact reject context по выбранному `payload_hash`.
- **Top Reject Reasons / Fields / Signatures**: агрегаты в том же scoped контексте.
- **Datasource**: `Quarantine Explorer` (JSON/Infinity), не Prometheus.
- **Scope contract**: `$pipeline` всегда single-select/no-All; `run_id` и
  `payload_hash` остаются Explorer-only forensic filters.
- **Drilldown**: top-level bus links `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`;
  row-level link в CLI-команду остаётся для action handoff.

#### 5. Workflow

Prometheus dashboard для declarative workflow orchestration. Используйте его,
когда pipeline-level панели зелёные, но workflow DAG показывает failed/skipped
step outcomes.

- **Workflow Runs**: selected-range count по `bioetl_workflow_runs_total`.
- **Step Outcomes by Kind**: breakdown по bounded `step_kind/status` без
  `run_id` или `step_id` labels; panel now respects selected `$status`.
- **Step Duration p95**: latency по `bioetl_workflow_step_duration_seconds`;
  panel now also respects selected `$status`.
- **Drilldown**: links `0. Control Plane`, `1. Overview`, `2. Runtime`,
  `3. Provider Health`, `4. Data Quality`.

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
- Для row-level browsing переходите в `Silver Reject Explorer`.
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
  1. Перейдите в `Silver Reject Explorer` для списка записей и detail по `payload_hash`.
  1. Если нужны action-операции, используйте quarantine CLI (`inspect/resolve/replay`).
- **`Silver Reject Explorer` показывает `No data` во всех панелях**:
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
