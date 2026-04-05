______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# 05.01 Руководство по мониторингу (Monitoring Guide)

*Reference: [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Мониторинг ориентирован на локальный процесс BioETL и локальные endpoint'ы метрик.

BioETL использует стек **Prometheus + Grafana** для обеспечения полной наблюдаемости за процессом сбора и трансформации данных. Данный документ описывает структуру системы, доступные дашборды и способы интерпретации данных.

`Observability Checklist` complements this guide: use this page for observability
surface interpretation and shipped alert semantics, and use
[runbooks/observability-checklist.md](runbooks/observability-checklist.md) for
operator validation and incident-readiness checks.

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

> **Важно**: Если вы не видите данных, убедитесь, что в фильтре выбран правильный пайплайн или стоит значение `All`.

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

- **Warnings / Unstructured Logs**: range-based count structured warning logs и unstructured rows по текущему `$pipeline`.

- **Pipeline / DQ / Control-plane / Provider / Freshness Alert Conditions**: Prometheus-backed stat panels, которые отражают те же условия, что и alert rules, но не притворяются real alert-state engine.

- `Pipeline / DQ / Control-plane / Provider / Freshness Alert Conditions` теперь считают
  количество активных семейств условий, а не сырые суммы event counters.

- **Top Warning Events**: быстрый range-based срез наиболее частых warning events.

- **Log Hygiene Trend**: короткий timeseries-тренд warnings vs unstructured rows через `$__interval`.

- **Drilldown**: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)` и data links у `Log Hygiene Trend` ведут в Explore с тем же временным окном.
  Для Tempo runtime surface использует TraceQL filter по текущим `$pipeline/$run_type`, а не пустой search.

- **DQ Context Failures (24h) / DQ Reports Skipped (24h) / DQ Reports Generated (24h)**:
  lifecycle counters для DQ reporting. Используйте их, когда нужно быстро
  понять, не сломалась ли сборка DQ context, отчёты системно пропускаются или
  наоборот стабильно доходят до успешной генерации.

- **Trace-enabled Runs (24h)**: показывает, были ли за окно запуски с реальным
  tracing path. Если здесь `0`, пустой Tempo для выбранного `$pipeline/$run_type`
  ожидаем. Если здесь значение больше нуля, а `Explore Traces (Tempo, tracing profile)` пуст,
  это уже сигнал разбирать exporter / flush / ingestion path.

- **Pipeline Alert Conditions (15m)**: fleet-wide срез по трем главным runtime
  рискам: preflight `data_source`, `infrastructure_validated` и
  `pipeline_runs_total{status="failed"}`. Если панель активна, расследование
  стоит начинать с `pipeline-failure-critical.md`, а не только с provider/DQ path.

- **Global Control-plane Lookup Outcomes (1h) / Global Control-plane Lookup p95 (1h)**:
  runtime-срез по success/miss/failed для manifest, ledger и lineage lookup
  paths. Эти панели особенно полезны, когда write-side выглядит здоровым, но
  follow-up investigation или lineage drilldown начинают терять данные. Они не
  привязаны к `$pipeline`, потому что underlying control-plane read metrics не
  несут pipeline label.

#### 3. 3. Provider Health

Технический мониторинг состояния внешних API (ChEMBL, UniProt и др.).

- **Health Check Latency by Provider (p95)**: тренд латентности провайдеров.
- **Healthy Checks / Degraded Checks / Health Checks Total**: разделяют completed probes по outcome и не маскируют `DEGRADED` как success.
- **Per-provider gauge (102)**: повторяемая p95-панель по `$provider`.
- **Drilldown**: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)`
  и data links у latency-панели открывают correlation path. Для Loki shipped
  baseline стартует с общего `{job="bioetl"}` stream, а дополнительное
  сужение по `provider` оператор делает уже в Explore. Tempo handoff здесь сразу
  использует `span."bioetl.provider"` для текущего `$provider`.

#### 4. 4. Data Quality

Сфокусирован на чистоте данных и аномалиях.

- **Data Quality Score (Volume-weighted)**: volume-aware gauge на базе
  `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`.
- **Worst-Entity DQ Score**: быстрый worst-case сигнал по сущностям в выбранном pipeline scope.
- **Quarantine / Soft Threshold / Validation Failures**: контроль деградаций по окнам времени.
- **Anomalies / DQ p95 / Data Freshness**: детальные DQ-сигналы.
- **Drilldown**: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` / `Explore Traces (Tempo, tracing profile)`
  и data links у `Data Flow in Range: Bronze -> Silver -> Gold` переводят расследование
  DQ incidents и freshness lag в Grafana Explore с тем же временным окном.
  Tempo handoff уже ограничен текущими `$pipeline/$run_type`.

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
     `lineage_fragment_ids`, `missing_artifact_links`.
  1. Если проблема связана с resume, откройте runbook
     `checkpoint-debugging.md`.

## 6. Ссылки

- [Архитектурное решение ADR-017 (Observability)](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [Правила именования метрик (RULES.md)](../00-project/RULES.md)
