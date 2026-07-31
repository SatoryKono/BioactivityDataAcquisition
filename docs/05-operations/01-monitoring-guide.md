______________________________________________________________________

Version: 1.4.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-30'

______________________________________________________________________

# 05.01 Руководство по мониторингу (Monitoring Guide)

*Reference: [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Мониторинг ориентирован на локальный процесс BioETL и локальные endpoint'ы метрик.

BioETL использует стек **Prometheus + Grafana** для обеспечения полной наблюдаемости за процессом сбора и трансформации данных. Данный документ описывает структуру системы, доступные дашборды и способы интерпретации данных.

The optional `bioetl-scenes-app` is a read-only shadow presentation adapter and
is not part of default provisioning. The seven JSON UIDs remain the supported
fallback; disabling the app restores JSON-only operation without changing
BioETL core. See
[Scenes dual path](../03-guides/dashboards/scenes-dual-path.md).

`Observability Checklist` complements this guide: use this page for observability
surface interpretation and shipped alert semantics, and use
[runbooks/observability-checklist.md](runbooks/observability-checklist.md) for
operator validation and incident-readiness checks.

`SLI/SLO Baseline` complements both documents: use
[sli-slo-baseline.md](sli-slo-baseline.md) for numeric operational objectives,
target windows, and alert-to-SLI mapping.

Shipped dashboard inventory, JSON mapping, and naming/versioning policy now
live in [../03-guides/dashboards/dashboard-inventory.md](../03-guides/dashboards/dashboard-inventory.md).

## 0. Канонический operator workflow

Dashboard System 2.0: **detect → localize → decide → recover**.
Phase-1 epic #6800 + Phase-2 residual epic #6828.
UI entry is evidence-first: Fleet (`bioetl-overview-v2`) or Incident Workspace
(`bioetl-incident-v1`) for alert hops; Trust for resume safety; Run Explorer for
exact identity. Navigation bus `0..6` on every board.
See [operator-ux-v2.md](../03-guides/dashboards/operator-ux-v2.md),
[dashboard-system-2.0-phase2-residual.md](../03-guides/dashboards/dashboard-system-2.0-phase2-residual.md),
and [migration-map-v2.md](../03-guides/dashboards/migration-map-v2.md).
Record forensics remain CLI (`bioetl quarantine inspect`) — no Loki/Tempo UI.

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
1. `python -m scripts.engineering.qa report-observability-metric-inventory --typed-observability-views --json` —
   source-specific inventory for recording outputs, policy aliases, direct
   dashboard targets, recording-rule inputs, direct alert inputs, and HTTP
   panel endpoints. It fails closed on one-way output/declaration drift and on
   any Prometheus selector that leaks `run_id`.
1. Сравните inventory output с
   `grafana/prometheus-rules/bioetl_observability.yml` и shipped dashboard JSON
   до того, как трактовать missing panels как runtime outage.

Важно:

- metrics HTTP server startup остаётся auto-managed during normal pipeline runs;
- Pushgateway publication остаётся best-effort on run completion; CLI runs do
  not fail solely because publication fails, but publication helpers propagate
  failed push results for diagnostics and emit bounded publication status
  metrics;
- Pushgateway snapshots are grouped only by bounded `pipeline` and `run_type`,
  so short-lived ChEMBL runs remain queryable after process exit without
  introducing occurrence-scoped labels such as `run_id`;
- Forbidden Prometheus label names (including aliases such as
  `filesystem_path` and `raw_exception_message`) are denied by registry policy
  in `prometheus_metric_label_policy_sets.FORBIDDEN_PROMETHEUS_LABEL_NAMES`.
  Instant-query emptiness for forbidden labels proves **current** compliance
  only. Retained historical series (for example older `run_id`-bearing
  `bioetl_records_processed_*` samples) may still exist until Prometheus
  retention expires them. Operators must report current violations separately
  from retained stale series and must not perform destructive TSDB cleanup
  unless an explicitly approved, recoverable procedure is used;
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

Loki/Tempo **не** входят в shipping monitoring surface (removed 2026-07-23).
Use structured application logs and Prometheus metrics for local ops; optional
external log/trace backends are BYO.

## 2. Использование дашбордов

Этот guide владеет operator workflow, но не повторяет panel inventory. JSON,
версии и datasources принадлежат
[Dashboard Inventory](../03-guides/dashboards/dashboard-inventory.md); точные
панели, формулы, queries и no-data semantics принадлежат seven canonical
файлам `docs/03-guides/dashboards/panels/*-panels.md` (Silver Reject Explorer
panel guide is historical only).

### Маршрутизация расследования

Shipped portfolio is **seven boards** (nav bus `0..6`). Retired JSON
(`bioetl-workflow-overview`, `bioetl-alerts-slo`, `bioetl-silver-reject-explorer`)
is not a routing target — see
[Dashboard Inventory](../03-guides/dashboards/dashboard-inventory.md) and
[monitoring-surface-reduction-2026-07-23](runbooks/monitoring-surface-reduction-2026-07-23.md).

| Вопрос | Dashboard | Следующий шаг |
| --- | --- | --- |
| Общий статус run / fleet | `1. Overview` | Зафиксировать scope и точный `run_id` (Ops HTTP identity, not a Prom label). |
| Manifest, ledger, checkpoint, replay safety | `0. Trust` (Control Plane) | Проверить lifecycle evidence; resume safety. |
| Ошибка, latency, stage accounting | `2. Pipeline Diagnostics` (Runtime) | Workflow step band lives here; open related runbook. |
| Provider availability / adapter errors | `3. Provider Health` | Provider/adapter scope and cause taxonomy. |
| DQ contract / soft-hard thresholds | `4. Data Quality` | Разделить Silver rejects vs Gold strict failures. |
| Multi-domain triage / alert hop | `5. Incident Workspace` | Domain suspects (Runtime / Provider / DQ) + ALERTS support. |
| Exact completed-run identity | `6. Run Explorer` | Ops HTTP run report; never Prom `run_id` labels. |
| Alert / SLO triage | `1. Overview` (collapsed Alert/SLO row) + §3 below | No separate Alerts & SLO dashboard JSON. |
| Silver / quarantine rejects | CLI `bioetl quarantine inspect` (+ aggregates on `4. Data Quality`) | Explorer UI removed 2026-07-23; actions remain CLI. |

`OK/WARN/CRIT` — business severity; `INCOMPLETE` — неполное evidence;
`UNKNOWN` — отсутствие честного verdict; `ERROR` — query/datasource/backend
failure. `VALID EMPTY`, `TELEMETRY ABSENT` и `N/A` различаются. `LOADING`
временно; пустая панель не является evidence.

На первом экране сначала прочитайте 18px вопрос в `Inspect Scope & Evidence`,
затем 16px scope-строки. `CURRENT`, `SELECTED RUN`, `TIME RANGE`, `FLEET` и
другие явно названные области обозначают разные основания evidence и не должны
интерпретироваться как peer status cards. В Run Explorer эту роль выполняет
`Inspect Run Selection & Evidence`.

Dashboard остаётся read-only surface. Replay и quarantine actions выполняются
через supported CLI после фиксации scope; изменение query или DQ threshold не
является recovery.

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

### Published-port smoke baseline

Когда dashboards и container health выглядят корректно, но host-side доступ к
`localhost:3000` / `localhost:9090` ведёт себя нестабильно, используйте
published-port smoke instead of guessing from container status:

```bash
python -m scripts.ops check-observability-ports --json
```

Интерпретация:

- `healthy`: host-published URL и container-internal endpoint оба healthy.
- `published_port_unreachable_but_container_healthy`: dashboards/rules внутри
  стека живы, а проблема находится в host port publishing, WSL/localhost
  forwarding, firewall, VPN, proxy или local transport path.
- `published_and_container_unhealthy`: broken не только published port, но и
  внутренний service endpoint; начинайте с container/runtime triage.

## 4. Гарантии качества мониторинга

Все конфигурации дашбордов проходят автоматическую проверку (**Contract Testing**). Это гарантирует, что:

1. Дашборды используют только реально существующие в коде метрики.
1. На всех панелях настроены правильные единицы измерения (nM, bytes, sec).
1. Переменные фильтрации `$pipeline`, `$run_type` и `$provider` работают корректно.

Подробнее см. в документации по тестированию наблюдаемости.

### Prometheus / Pushgateway compatibility contract

| Component | Supported series | Validation path |
| --- | --- | --- |
| Prometheus and `promtool` | `3.13.x` (QA image `prom/prometheus:v3.13.1`) | `python -m scripts.engineering.qa check-prometheus-rules --runner docker --coverage-json` checks both shipped rule files and the shared fixture |
| Pushgateway | `1.11.x` | monitoring profile health plus `pushgateway_build_info`; publication remains bounded to `pipeline,run_type` |

The monitoring profile and CI/QA `promtool` MUST stay on the same Prometheus
major/minor series. A version change requires updating this matrix, the pinned
QA image, rule fixtures, and monitoring-profile pins in one reviewed change.

## 5. Что делать если... (Runbook Lite)

- **График "Error Rate" покраснел**: Используйте `structlog` для получения деталей исключений.
- **Вырос `Track: Silver Filter Rejects in Range`**:
  1. Подтвердите spike в `1. Overview` или `2. Runtime`.
  1. Перейдите в `4. Data Quality` и проверьте `Inspect: Top Silver Reject Reasons (Pareto)` /
     `Inspect: Top Silver Reject Fields`.
  1. Для record-level списка используйте CLI:
     `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only ...`
     (Grafana Silver Reject Explorer UI removed 2026-07-23).
  1. Action-операции: quarantine CLI (`inspect/resolve/replay/purge`).
- **Identity / Processed Records cards показывают `No data`**:
  1. Проверьте main health server: `curl http://127.0.0.1:8000/health/live`.
  1. Убедитесь, что Grafana datasource **BioETL Ops HTTP** указывает на
     `http://bioetl:8000` (или `BIOETL_OPS_HTTP_URL` override).
  1. Infinity plugin must be available for HTTP panels
     (`yesoreyeram-infinity-datasource`).
  1. Если Grafana уходит в restart loop, проверьте `docker logs bioetl-grafana`:
     shipped bootstrap entrypoint удаляет stale local `grafana-image-renderer`
     plugin из persistent volume, когда включён remote renderer sidecar.
  1. Если Grafana Render API (`/render/...`) возвращает `500`, пересоздайте
     `renderer` и `grafana` из текущего `docker-compose.monitoring.yml`
     (opt-in monitoring stack).
- **Дашборд пустой**:
  1. Проверьте, что пайплайн-процесс запущен и не завершился с ошибкой.
  1. Убедитесь, что пайплайн запущен с метриками (`BIOETL_METRICS_ENABLED=true`).
  1. Проверьте доступность endpoint метрик на порту 8000 (`/metrics`).
- **Grafana/Prometheus container healthy, но `localhost:3000` / `localhost:9090`
  из shell или браузера не открываются**:
  1. Запустите `python -m scripts.ops check-observability-ports --json`.
  1. Если diagnosis=`published_port_unreachable_but_container_healthy`,
     считайте это published-port / host transport defect, а не broken dashboard JSON.
  1. Проверьте Docker Desktop localhost forwarding, WSL-to-host networking,
     local firewall/VPN/proxy filtering и опубликованные `ports:` в
     `docker-compose.monitoring.yml`.
  1. Для container-internal proof используйте:
     `docker exec bioetl-grafana wget -qO- http://127.0.0.1:3000/api/health`
     и
     `docker exec bioetl-prometheus wget -qO- http://127.0.0.1:9090/-/healthy`.
- **Нет логов / traces в Grafana Explore (Loki/Tempo)**:
  1. Loki/Tempo **не** входят в shipping monitoring surface (removed 2026-07-23).
     Не диагностируйте BioETL run через Grafana Loki/Tempo UI на default stack.
  1. Используйте локальный structured log surface (например `reports/logs/bioetl.log`
     или process stdout) и Prometheus metrics / shipped boards.
  1. Optional external log/trace backends are BYO; empty Explore is expected when
     those backends are not provisioned.
- **Метрики показывают UNHEALTHY для storage**: Проверьте права доступа к папкам `data/`.
- **Control-plane сигналы стали красными**:
  1. Запустите `bioetl run-manifest show <run-id|manifest-id> --format json`.
  1. Проверьте `diagnostics.alert_signals`, `artifact_refs`,
     `artifact_refs[*].artifact_id`, `lineage_fragment_ids`,
     `missing_artifact_links`.
  1. Если проблема связана с replay/checkpoint/resume, откройте
     `checkpoint-debugging.md`; exact manifest/ledger identity evidence
     подтверждайте через `run-manifest-inspection.md`.

## 6. Ссылки

- [Архитектурное решение ADR-017 (Observability)](../02-architecture/decisions/ADR-017-observability-architecture.md)
- [Правила именования метрик (RULES.md)](../00-project/RULES.md)
