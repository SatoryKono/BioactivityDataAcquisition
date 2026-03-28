# 05.01 Руководство по мониторингу (Monitoring Guide)

*Reference: [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Мониторинг ориентирован на локальный процесс BioETL и локальные endpoint'ы метрик.

BioETL использует стек **Prometheus + Grafana** для обеспечения полной наблюдаемости за процессом сбора и трансформации данных. Данный документ описывает структуру системы, доступные дашборды и способы интерпретации данных.

## 1. Архитектура наблюдаемости

Система мониторинга построена на принципе "Pull":
1.  **BioETL App**: При запуске пайплайна поднимает временный HTTP-сервер (порт 8000), экспортирующий метрики в формате OpenMetrics.
2.  **Prometheus**: Регулярно собирает (scrape) метрики из приложения и сохраняет их в базе данных временных рядов (TSDB).
3.  **Grafana**: Выступает в роли интерфейса визуализации, подключаясь к Prometheus как к источнику данных.

## 2. Использование Дашбордов

Все дашборды в BioETL v5.1+ поддерживают **динамическую фильтрацию**.

### Фильтрация и Изоляция данных
В верхней части каждого дашборда расположены выпадающие списки:
- **Simple / Overview v2 / DQ v2**: `$pipeline`, `$run_type`
- **Provider Health v2**: `$provider`

> **Важно**: Если вы не видите данных, убедитесь, что в фильтре выбран правильный пайплайн или стоит значение `All`.

### Основные Дашборды

#### 1. BioETL Overview v2
Центральный дашборд для контроля за выполнением пайплайнов.
- **Processing Pipeline**: динамика по стадиям (bronze/silver/gold/quarantined).
- **Stage Distribution / Pipeline Distribution**: срезы распределения.
- **Overall Quality**: `gold / clamp-min(bronze, 1)`.
- **Control Plane & Lineage**: отдельная строка для `Manifest Writes (24h)`,
  `Ledger Appends (24h)`, `Checkpoint Incompatibilities (24h)` и
  `Lineage Fragment Failures (24h)`.
- **Lineage Fragment Outcomes (1h)**: тренд публикации lineage fragments по
  `layer/status` без использования high-cardinality labels.
- **Drilldown**: dashboard links `Explore Logs (Loki)` / `Explore Traces (Tempo)`
  и data links у `Processing Pipeline` переводят оператора в Grafana Explore с тем
  же временным окном.

#### 2. BioETL Data Quality v2
Сфокусирован на чистоте данных и аномалиях.
- **Data Quality Score**: `(gold + quarantined) / clamp-min(bronze, 1)`.
- **Quarantine / Soft Threshold / Validation Failures**: контроль деградаций по окнам времени.
- **Anomalies / DQ p95 / Data Freshness**: детальные DQ-сигналы.
- **Drilldown**: dashboard links `Explore Logs (Loki)` / `Explore Traces (Tempo)`
  и data links у `Data Flow: Bronze -> Silver -> Gold` переводят расследование
  DQ incidents и freshness lag в Grafana Explore с тем же временным окном.

#### 3. BioETL Provider Health v2
Технический мониторинг состояния внешних API (ChEMBL, UniProt и др.).
- **Health Check Latency by Provider (p95)**: тренд латентности провайдеров.
- **Health Check Successes (15m) / Health Checks (15m)**: текущий объём и стабильность health_check без lifetime-counter шума.
- **Per-provider gauge (102)**: повторяемая p95-панель по `$provider`.
- **Drilldown**: dashboard links `Explore Logs (Loki)` / `Explore Traces (Tempo)`
  и data links у latency-панели открывают correlation path для выбранного
  провайдера.

## 3. Alert-backed сигналы

Для shipped observability baseline дополнительно отслеживаются:

- **Control plane / traceability**
  - `BioETLControlPlaneManifestWriteFailed` -> `run-manifest-inspection.md`
  - `BioETLRunLedgerAppendFailed` -> `run-manifest-inspection.md`
  - `BioETLCheckpointCompatibilityBlocked` -> `checkpoint-debugging.md`
  - `BioETLLineageFragmentPersistenceFailed` -> `traceability-signal-ownership.md`
  - `BioETLLineageRefsMissing` -> `traceability-signal-ownership.md`
- **DQ / freshness**
  - `BioETLDQSoftThresholdExceeded` -> `dq-failure-investigation.md`
  - `BioETLDQQuarantineRateHigh` / `BioETLDQQuarantineRateCritical` -> `dq-failure-investigation.md`
    (`5-20%` warning / `>20%` critical, только при `bronze>=20`)
  - `BioETLDQValidationFailuresCritical` -> `dq-failure-investigation.md`
  - `BioETLDQCriticalAnomaliesDetected` -> `dq-failure-investigation.md`
  - `BioETLSilverValidationFailuresDetected` -> `dq-failure-investigation.md`
  - `BioETLDataFreshnessLagHigh` / `BioETLDataFreshnessLagCritical` -> `dq-failure-investigation.md`
    (`24-72h` warning / `>72h` critical)
- **Provider health**
  - `BioETLProviderFailureRateHigh` -> `incident-response.md`
  - `BioETLProviderRetriesExhausted` / `BioETLProviderRetriesExhaustedPersistent` -> `incident-response.md`
    (`1-2` exhaustions per `1h` warning / `>=3` critical)

## 4. Гарантии качества мониторинга

Все конфигурации дашбордов проходят автоматическую проверку (**Contract Testing**). Это гарантирует, что:
1.  Дашборды используют только реально существующие в коде метрики.
2.  На всех панелях настроены правильные единицы измерения (nM, bytes, sec).
3.  Переменные фильтрации `$pipeline`, `$run-type` и `$provider` работают корректно.

Подробнее см. в документации по тестированию наблюдаемости.

## 5. Что делать если... (Runbook Lite)

- **График "Error Rate" покраснел**: Используйте `structlog` для получения деталей исключений.
- **Дашборд пустой**: 
    1. Проверьте, что пайплайн-процесс запущен и не завершился с ошибкой.
    2. Убедитесь, что пайплайн запущен с метриками (`BIOETL_METRICS_ENABLED=true`).
    3. Проверьте доступность endpoint метрик на порту 8000 (`/metrics`).
- **Метрики показывают UNHEALTHY для storage**: Проверьте права доступа к папкам `data/`.
- **Control-plane сигналы стали красными**:
    1. Запустите `bioetl run-manifest show <run-id|manifest-id> --format json`.
    2. Проверьте `diagnostics.alert_signals`, `artifact_refs`,
       `lineage_fragment_ids`, `missing_artifact_links`.
    3. Если проблема связана с resume, откройте runbook
       `checkpoint-debugging.md`.

## 6. Ссылки
- [Архитектурное решение ADR-017 (Observability)](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [Правила именования метрик (RULES.md)](../00-project/RULES.md)
