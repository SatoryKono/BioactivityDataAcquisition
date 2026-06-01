______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

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

### Policy header для operator dashboards

Любой operator dashboard в BioETL должен с первого экрана отвечать на один
главный вопрос и явно показывать:

- `ONE BIG QUESTION`
- current scope
- provenance summary: source systems / metric families, cadence, transformation
  or runtime version, last successful run/refresh in UTC, owner/contact
- availability/risk notes: SLA, known limitations, sensitivity
- `First action`: что делать при `CRIT` и `WARN`

Canonical `1. Overview` (`bioetl-overview-v2`) now uses the frozen Overview v3
layout for this transition: explicit provenance header, aggregate-first status
cards, visible `workflow`/`run_id` context, and local control-plane identity
handoff in the compact `ID` panel. The panel shows `Run ID`, `Manifest ID`,
`Provider.Entity`, `Contract`, `Execution`, replay capability/mode, checkpoint
anchors, optional composite run identity, and identity health for the current
control-plane scope. `Run Type=All` трактуется как unbounded run-type filter;
`Pipeline=All` без exact `run_id` не должен притворяться одним manifest
identity.

Primary dashboards `0..5` now reuse the Overview-derived context shell:
`workflow`, `pipeline`, `run_type`, and HTTP-backed `run_id`, plus common
`Provenance`, `Status`, `ID`, and `Processed Records` panels. `run_id` remains
local HTTP identity context only; `Processed Records` may pass it to the local
backend for RunLedger exact-run accounting, but do not use it as a Prometheus
label or as a generic cross-dashboard filter.
If `ID` or `Processed Records` is empty, verify the Quarantine Explorer /
control-plane backend health (`/health/live`) before interpreting the card as
an absent run, expected empty scope, or zero processed records. The shipped
cards include no-value copy and backend-health links so backend-down is not
visually equivalent to valid zero evidence.

`0. Control Plane` keeps the compact shared `ID` panel backed by
`/ops/control-plane/identity-table`. It is a two-column operator summary, not a
Prometheus surface: full high-cardinality values stay in the HTTP table rows,
while dashboard stats and PromQL labels stay bounded. The deeper identity
evidence below fold uses `/ops/control-plane/identity-evidence` for P0/P1/P2
anchors, short/full value rendering, replay parentage, composite identity,
checkpoint anchor compare, identity gaps, typed source/drilldown metadata, and
copy-friendly full values without projecting high-cardinality IDs into
Prometheus labels.

### Фильтрация и Изоляция данных

В верхней части каждого дашборда расположены выпадающие списки:

- **0. Control Plane**: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- **1. Overview**: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- **2. Runtime / 4. Data Quality**: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`, `$stage`
- **3. Provider Health**: `$workflow`, `$pipeline`, `$run_type`, `$run_id`,
  `$provider` visible; `$adapter` hidden detail-only for cross-scope
  circuit-breaker diagnostics
- **Silver Reject Explorer**: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$quarantine_run_id`, `$payload_hash`
- **5. Workflow**: `$workflow`, `$pipeline`, `$run_type`, `$run_id`,
  `$status`, `$step_status`, `$step_kind`

> **Важно**: shipped dashboards используют общий context shell plus
> role-specific selectors, а не один flat universal query model.
> Канонический machine-readable selector contract:
> `docs/03-guides/dashboards/contracts/selector-contracts.yaml`.
> `$workflow` остаётся single-select with Include All на primary dashboards,
> включая `5. Workflow`, чтобы handoff сохранял один coherent workflow shell
> value без потери aggregate `All` scope.
> `1. Overview` допускает `Workflow=All`, `Pipeline=All`, `Run Type=All` и
> `Run ID=-` как shipped default entry scope. Pipeline-scoped L1 dashboards сохраняют scoped handoff через
> `$pipeline`/`$run_type`, а `3. Provider Health` получает hidden
> `$pipeline_context` для обратного перехода и fail-closed `provider=unknown`,
> если source dashboard не может доказать валидный provider label. Если
> реального scoped значения нет, используйте только те fallback-значения,
> которые разрешены `navigation-links.yaml`; если нужен role/family-level
> selector contract, используйте `selector-contracts.yaml`.

### Основные Дашборды

#### 1. Overview

L0 дашборд для одного operator question: что сейчас broken/degraded в BioETL и
куда drill down первым.

- **Answer surface**: `Provenance`, `Status`, `ID`, `Processed Records`,
  `First Action`, `Control Plane`, `Runtime`, `Data Quality`, `Provider`,
  `Data Validation`, `Inputs`, `Workflow`. `OK` requires recent signal; no
  recent samples stay `UNKNOWN`, not green. Workflow summary is current-state
  evidence and must follow the latest bounded terminal workflow signal rather
  than cumulative workflow-run counters.
- **Above-the-fold layout**: first screen without scroll contains the
  provenance header, `Status`, local identity context (`ID`), processed-record
  context, `First Action`, compact subsystem current-status cards, `Inputs`,
  and `Workflow`.
- **L1 historical context**: immediately below the first screen lives the
  `L1 Historical Trends` row with `Runtime Blockers Trend`, `DQ Status Trend`,
  and `Gold Lifecycle Trend`. Эти графики дают recent-history context и не
  заменяют current-status verdict.
- **Subsystem routing**: first-screen current-status panels показывают
  status-first verdict и panel-level drilldowns в canonical dashboards
  (`Runtime`, `Control Plane`, `Data Quality`, `Provider Health`,
  `Workflow`), а `Status` / `First Action` дают общий triage order.
  Provider handoff fail-close'ится к `provider=unknown` с сохранением
  `pipeline_context`; workflow handoff явно reset-scope.
- **Failure summary**: только compact selected-range summaries по manifest /
  ledger, checkpoint, lineage и `Silver Rejects + Rate`. Distribution
  pie panels, standalone vanity yield/rate gauges и composite source-selection
  detail не входят в L0 flow.
- **Expanded rows**: `Range Evidence` содержит
  `Historical Failures`, `Recent Terminal Runs` и `Silver Rejects + Rate`;
  `Diagnostics & Docs` остаётся отдельной
  expanded navigation/support surface.
- **Drilldown**: top-level шина содержит `0. Control Plane`, `2. Runtime`,
  `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `Silver Reject Explorer`;
  ключевые current-status panels дублируют этот handoff через panel `dataLinks`.
  Каноническая shipped surface этой шины — navigation panel `id=1000`; header
  row рядом с Grafana variables не обязан повторять те же dashboard links.
  Для `bioetl-control-plane-v1` top-level navigation намеренно не уводит
  оператора напрямую в Grafana Explore apps: first screen остаётся dashboard +
  runbook surface, а logs/traces расследование начинается из связанных
  dashboard handoff и runbook-пути.

#### 2. 2. Runtime

`2. Runtime` теперь является **L2 diagnostic dashboard**. Его primary question:
где pipeline runtime теряет время, падает, копит backlog или даёт
warning/error conditions. Dashboard остаётся **Prometheus-first**:
answer row, latency/localization и handoff-панели usable без Loki/Tempo, а
tracing-backed log hygiene живёт в expanded row
`Tracing-only Log Hygiene (requires optional tracing profile)`.

- **Top answer area**:
  `Monitor Runtime Current Status` and `Inspect Top Runtime Blockers` share the
  current-cause row. The compact evidence row contains
  `Monitor Worst Stage Lag`, `Monitor Runtime Blockers`,
  `Monitor Runtime Error Rate`, `Monitor Runtime Telemetry Gap`, and
  `Monitor Failed Runs`; `First Action` remains a full-width operator CTA below
  those compact rows.
  Это первый экран triage. Если здесь уже понятно, что runtime blocked,
  оператор не должен сначала прокручивать в logs/traces.
  `Monitor Runtime Telemetry Gap` проверяет scrape plus runtime dashboard
  recording-rule evaluation failures, rule-group presence and evaluation
  freshness; non-zero/UNKNOWN делает zero-count panels inconclusive.
  Это intentional datasource trust marker: runtime сохраняет явный first-screen
  health signal только там, где без него zero-count cards можно спутать с
  healthy state.
  `Monitor Worst Stage Lag`, `Monitor Failed Runs` и
  `Monitor Runtime Error Rate` остаются selected-range evidence; они не
  определяют current status.
  `Inspect Active Runtime Blocker Detail` открывается как expanded `Detect`
  drilldown, а не как отдельная first-screen guidance panel.

- **Localization row**:
  `Stage Backlog Trend`, `Records by Stage / Interval`,
  `Pipeline Phase Duration p50/p95/p99`,
  `Pipeline Duration p50/p95/p99`,
  `Errors by Stage / Error Code / Range`,
  `Records by Stage / Run Type / Range`.
  Эти панели отвечают на вопрос, в каком stage/phase runtime теряет время,
  поток записей или стабильность. Synthetic `none=0` series в distribution
  panels являются empty-state placeholders, а не реальными telemetry labels.

- **Handoff row**:
  `Pipeline Alert Conditions`, `DQ Alert Conditions`,
  `Control-plane Alert Conditions`, `GLOBAL Provider Alert Conditions`,
  `Freshness Alert Conditions`,
  `Track GLOBAL Shutdown Initiated by Reason / Interval`,
  `Track GLOBAL Shutdown Completed by Reason / Interval`.
  Это именно compact handoff surfaces, а не попытка дублировать DQ,
  Provider Health или Control Plane dashboards. `0` на handoff cards допустим
  только когда selected runtime universe или GLOBAL provider current-status
  telemetry подтверждает scope; отсутствующий scope остаётся `UNKNOWN`.

- **Alert/SLO triage surface**:
  `1. Overview` includes expanded `Alert/SLO Triage` with
  `Triage Alert State`. This panel reads Prometheus `ALERTS` for firing and
  pending alert state, preserving the alert-rule source of truth instead of
  re-encoding alert thresholds in dashboard queries.

- **Logs/traces row**:
  `Warnings`, `GLOBAL Unstructured Logs`, `Top Warning Events by Message / Range`,
  `GLOBAL Log Hygiene Trend`
  остаются shipped, но вынесены в expanded tracing-only row. Если tracing
  profile выключен, оператор всё равно получает usable runtime triage без Loki
  и Tempo. `Inspect GLOBAL Unstructured Logs` показывает parsed `.__error__`
  из Loki pipeline после `| json`; эти rows intentionally GLOBAL, потому что
  parser failures нельзя безопасно scoped by `$pipeline`.

- **Drilldown contract**:
  navigation bus `0. Control Plane`, `1. Overview`, `3. Provider Health`,
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

- **Monitor GLOBAL Provider Severity Matrix / Inspect Critical Providers / Inspect Provider Top Causes**:
  first-screen triage для fleet-wide provider состояния. Matrix intentionally
  остаётся GLOBAL и читает canonical `bioetl_provider_current_status`;
  missing current-status telemetry должно оставаться `UNKNOWN`, а не
  маскироваться под `OK`. Panel `Inspect Critical Providers` intentionally
  показывает только active `DEGRADED`/`FAILING`; providers с missing telemetry
  остаются в severity matrix как `UNKNOWN`. `Inspect Critical Providers` и
  `Inspect Provider Top Causes` дают direct handoff в canonical provider
  incident runbook. `Inspect Provider Top Causes` может оставаться непустой
  даже при `GLOBAL severity = OK`, потому что canonical cause projection
  deliberately включает early-warning provider signals независимо от
  current-status projection; трактуйте это как diagnostic lead и сначала
  подтверждайте raw provider status plus selected-range provider evidence before
  replay or escalation. Если provider severity non-OK, а canonical cause
  projection пуста, трактуйте это как explainability gap и проверяйте raw
  provider status plus optional rate-limit/circuit-breaker telemetry before
  replay or escalation.
- **Monitor Provider Telemetry Freshness**: first-screen trust marker for
  `bioetl_provider_current_status`; `0=OK`, `1=WARN`, `null=UNKNOWN`.
  WARN here means no current-status samples in the active Grafana time range, so an empty
  severity matrix is a telemetry gap, not proof that providers are healthy.
- **Review Raw Provider Health Enum**: table panel по
  `bioetl_provider_health_status{provider}` с fail-closed fallback через
  provider universe and selected-range lookup и явным mapping:
  `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`, `null/NaN=UNKNOWN`. Use it as
  supporting evidence when `Status=UNKNOWN` or when top causes and first-screen
  severity disagree.
- **Track Health Check Latency by Provider (p95)**: selected-range тренд латентности провайдеров.
- **Monitor Healthy Checks (Selected Range) / Monitor Degraded Checks (Selected Range) / Track Health Checks Total (Selected Range)**: selected-range evidence по completed probes; эти панели не являются current-health source.
- **Track Provider Failure Rate (Selected Range)**: selected-range failure ratio
  uses the policy thresholds `5%` warning / `20%` critical.
- **Failure & Degraded Trend by Provider**: показывает устойчивость деградации по каждому provider в выбранном time range.
- **Track Provider Failure Share (Selected Range)**: ранжирует providers по доле failed probes внутри активного scope.
- **Retries Exhausted by Provider / Operation** и **Retries Exhausted Trend by Provider / Operation**:
  показывают, где и насколько часто исчерпываются retries (`bioetl_data_source_retry_exhausted_total`).
- **Per-provider gauge (102)**: повторяемая p95-панель по `$provider`.
- **Inspect Adapter Request Latency by Endpoint (p95)**: endpoint-level inspect
  panel в секундах; red band matches the degraded provider rule at `>5s`, lower
  bands are earlier-warning diagnostics.
- **Track Rate Limiter Wait by Provider (p95)** и
  **Monitor Minimum Rate Limiter Tokens Available**: selected-range evidence
  для rate-limit pressure. Wait panel keeps an earlier-warning yellow band below
  the degraded-rule threshold `>1s`. Token panel preserves `No data` as a
  telemetry gap instead of synthesizing token depletion.
- **Monitor Cross-Scope Adapter Circuit Breaker State (max)** и
  **Track Cross-Scope Adapter Circuit Breaker Trips**: intentionally
  cross-scope adapter diagnostics, потому что shipped circuit-breaker metric
  family маркируется label `adapter`, а не `provider`. Missing trip/state
  samples remain diagnostic and do not create synthetic `adapter=none` or
  implicit `CLOSED` evidence.
- Для provider/control-plane/runtime/DQ latency panels `No data` нужно читать
  как “в окне нет latency samples”, а не как нормализованный `0s`.
- **Drilldown**: navigation bus `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `4. Data Quality`, `5. Workflow`, `Explore Logs`,
  `Explore Traces`, `Silver Reject Explorer`. Provider correlation по-прежнему
  идёт через Runtime/DQ переходы и runbook links; sticky shortcuts в `id=1000`
  не заменяют canonical provider triage flow.

#### 4. 4. Data Quality

Сфокусирован на текущем DQ incident state и selected-range evidence.

- **First answer row**: `Monitor DQ Current Status`,
  `Monitor DQ Threshold State`, `Inspect DQ Current Reasons` и
  `Review: First Action` отвечают, является ли DQ сейчас
  `OK`, `WARN`, `CRIT` или `UNKNOWN`. Disabled/noop DQ monitoring must appear
  as `WARN` or `UNKNOWN`, not as unconditional green.
- **Current-context row below the answer row**: `Monitor: Data Quality Score
  (Volume-weighted)`, `Monitor: Worst-Entity DQ Score`,
  `Monitor: Worst Data Freshness Lag (seconds)`, `Track: Records Quarantined in Range`,
  `Track: Soft Threshold Exceeded in Range` и `Track: Silver Filter Rejects in Range`
  дают compact supporting context до перехода к full-width historical evidence.
- **Track Range Evidence: Bronze -> Silver -> Gold**: полноширинный
  selected-range flow panel ниже current-context row.
- **Monitor: Silver Validation Failures / Gold Strict Validation Failures / Track: DQ Blocked Records in Range (Evidence) / Track: DQ Threshold Events in Range Trend**:
  контроль hard-failure и operator impact surfaces ниже first-screen band. Blocked-record
  и threshold-event панели показывают absolute evidence + domain threshold counters, а
  severity-вердикт остаётся за `Monitor DQ Current Status` / `Monitor DQ Threshold State`
  (без UI-side ratio math).
- **Anomalies / DQ p95 / Data Freshness**: детальные DQ-сигналы. `Worst Data
  Freshness Lag (seconds)` теперь показывает самый stale entity в выбранном
  scope через `max(time() - bioetl_data_freshness_seconds)`, а
  `Review: Latest Successful Data Timestamp` остаётся отдельным latest-success anchor
  на первом экране. Это intentionally разные сигналы: latest success не должен
  маскировать worst freshness lag.
- **Reject / Pareto / Fields** и
  **Validation Failures / Runtime Diagnostics / Trends** breakdown-панели
  сохраняют honest empty-state semantics: если в выбранном окне нет reject,
  quarantine или anomaly observations, панель остаётся пустой/`No data` и не
  синтезирует fake buckets вроде `pipeline=no_events`, `reason_code=none`,
  `field=none`, `error_type=none` или synthetic anomaly categories.
- **Reject / Pareto / Fields** теперь intentionally идёт в порядке
  `trust guard -> top reasons -> top fields -> pipeline distribution`, чтобы
  оператор сначала подтверждал корректность breakdown surface, а уже потом
  смотрел scope-distribution по `filtered_out`.
- **Inspect: Quarantine by Error Type** intentionally shipped как horizontal
  bar comparison surface, а не `piechart`: для quarantine triage сравнение
  категорий по объёму важнее процентной композиции.
- **Drilldown**: navigation bus `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `5. Workflow`, `Silver Reject Explorer`,
  `Explore Logs`, `Explore Traces`. Panel-level dashboard handoffs запрещены:
  replay/checkpoint traceability открывается через `0. Control Plane` в
  top-level шине.
  Tempo handoff uses bounded `$pipeline/$run_type` TraceQL scope.

#### Silver Reject Explorer

Record-level dashboard для `FILTERED_OUT_SILVER` записей (quarantine-backed, read-only datasource).

- **Filtered Records Table**: полный список отфильтрованных записей с server-side filtering/pagination.
- **Selected Record Details**: exact reject context по выбранному `payload_hash`.
- **Filtered Rejects Over Time / Reject Ratio vs Bronze Over Time**: temporal
  trend panels over the same scoped quarantine backend, useful to separate
  one-off spikes from sustained reject pressure.
- **Top Reject Reasons / Fields / Signatures**: агрегаты в том же scoped контексте.
- **Review: First Action / No-Data Semantics**: поясняет, когда `0` rejects является OK,
  а когда `No data`, `unknown` pipeline, unsupported filter chain,
  backend/plugin failure или `bronze_records=0` остаются UNKNOWN/error.
- **Datasource**: `Quarantine Explorer` (JSON/Infinity), не Prometheus.
- **Trust model**: Explorer intentionally uses explicit first-screen copy and
  panel descriptions instead of a dedicated datasource-health stat tile; treat
  empty tables as OK only after the CTA confirms valid scope and backend
  availability.
- **Custom noValue copy**: per-panel `noValue` strings here intentionally stay
  datasource-specific instead of collapsing into plain `UNKNOWN`, because they
  distinguish empty result, missing scoped summary, excluded record, and
  backend/API ambiguity.
- **Scope contract**: `$pipeline` всегда single-select/no-All; `run_id` и
  `payload_hash` остаются Explorer-only forensic filters.
- **Drilldown**: navigation bus `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`;
  DQ panels can now open scoped Explorer views directly for
  `reason_code`/`field` narrowing;
  row-level link в CLI-команду остаётся для action handoff.

#### 5. Workflow

Prometheus dashboard для declarative workflow orchestration. Используйте его,
когда pipeline-level панели зелёные, но workflow DAG показывает failed/skipped
step outcomes.

- **Workflow Runs**: selected-range count по `bioetl_workflow_runs_total`.
- **Missing data semantics**: first-screen workflow count cards intentionally
  render `0` for empty selected ranges because they are bounded event counters,
  not current-status panels. Этот `0` не доказывает, что workflow сейчас
  healthy/running; live current state remains out of scope for this dashboard.
- **Step Outcomes by Kind**: breakdown по bounded `step_kind/status` без
  `run_id` или `step_id` labels; panel now respects selected `$status` and
  lives under expanded row `Step Diagnostics`.
- **Step Duration p95**: latency по `bioetl_workflow_step_duration_seconds`;
  panel now also respects selected `$status` and lives under expanded row
  `Step Diagnostics`.
- **First Screen**: keep run/step failure cards, `Workflow Run Outcomes / Range`,
  and `First Action` visible before expanding detailed step
  diagnostics.
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
  подтвердить spike по `Track: Silver Filter Rejects in Range` в активном Grafana time range.
- После подтверждения переходите в `4. Data Quality`, где
  `Inspect: Silver Filter Rejects by Pipeline` показывает scope/distribution по
  stage-total `filtered_out`, а
  `Inspect: Top Silver Reject Reasons (Pareto)` и `Inspect: Top Silver Reject Fields` дают bounded cause
  summary без raw quarantine text.
- Для row-level browsing переходите в `Silver Reject Explorer`.
- CLI остаётся execution surface для replay/resolve:
  `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --run-id <run-id> --limit 200` и
  `bioetl quarantine resolve --pipeline <pipeline> --payload-hash <payload-hash> --status IGNORED`.
  Explorer table keeps payload-hash self-drilldown in the same tab, while the
  CLI `data:text/plain` handoffs intentionally open in a new tab.

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

## 5. Что делать если... (Runbook Lite)

- **График "Error Rate" покраснел**: Используйте `structlog` для получения деталей исключений.
- **Вырос `Track: Silver Filter Rejects in Range`**:
  1. Подтвердите spike в `1. Overview` или `2. Runtime`.
  1. Перейдите в `4. Data Quality` и проверьте `Inspect: Top Silver Reject Reasons (Pareto)` /
     `Inspect: Top Silver Reject Fields`.
  1. Перейдите в `Silver Reject Explorer` для списка записей и detail по `payload_hash`.
  1. Если нужны action-операции, используйте quarantine CLI (`inspect/resolve/replay`).
- **`Silver Reject Explorer` показывает `No data` во всех панелях**:
  1. Проверьте, что backend доступен и `pipeline` явно задан:
     `curl "http://127.0.0.1:8081/ops/quarantine/filter-options?pipeline=<pipeline_name>"`.
  1. Убедитесь, что в dashboard выбран конкретный `$pipeline` (single-select),
     а не общий scope.
  1. Проверьте, что сервер поднят с внешним bind для Grafana container:
     `bioetl quarantine serve --host 0.0.0.0 --port 8081`.
  1. Проверьте наличие Infinity plugin и datasource:
     `curl -u admin:<password> http://localhost:3000/api/datasources` должен содержать `Quarantine Explorer`,
     а `curl -u admin:<password> http://localhost:3000/api/plugins/yesoreyeram-infinity-datasource/settings`
     должен возвращать `200`.
  1. Для Grafana 12+ используйте `GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource`
     (legacy `GF_INSTALL_PLUGINS` оставляем только для обратной совместимости).
  1. Убедитесь, что Grafana datasource `Quarantine Explorer` указывает на
     `http://host.docker.internal:8081` через host-gateway mapping Grafana
     container (или ваш override `BIOETL_QUARANTINE_EXPLORER_URL`).
  1. Проверьте, что host-side backend запущен как
     `bioetl quarantine serve --host 0.0.0.0 --port 8081`.
  1. Если Grafana уходит в restart loop, проверьте `docker logs bioetl-grafana`:
     shipped bootstrap entrypoint удаляет stale local `grafana-image-renderer`
     plugin из persistent volume, когда включён remote renderer sidecar.
  1. Если Grafana Render API (`/render/...`) возвращает `500`, пересоздайте
     `renderer` и `grafana` из текущего `docker-compose.monitoring.yml`.
     Repo-backed renderer config должен использовать pinned
     `grafana/grafana-image-renderer:5.0.0`, matching
     `GF_RENDERING_RENDERER_TOKEN` / `AUTH_TOKEN`, `BROWSER_FLAGS` вместо
     legacy `RENDERING_ARGS`, `shm_size: 1gb` и Prometheus target
     `grafana-image-renderer`.
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
- **Loki drilldown не находит событие**:
  1. Сначала проверьте, что общий запрос `{job="bioetl"}` вообще возвращает строки.
  1. Zero lines могут быть легитимны, если Loki shipping/profile выключен или выбранный run не отгрузил BioETL streams в текущем окне.
  1. Если локальный `reports/logs/bioetl.log` содержит свежие строки BioETL run, а `{job="bioetl"}` пуст, считайте это ingestion defect и проверьте Promtail positions, container mounts и Loki ingestion limits.
  1. После этого сузьте запрос вручную по `pipeline`, `provider` или `stage` уже в Explore.
  1. Не полагайтесь на `$pipeline/$provider` interpolation внутри encoded Explore payload.
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
