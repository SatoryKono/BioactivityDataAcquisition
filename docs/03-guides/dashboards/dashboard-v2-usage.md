______________________________________________________________________

Version: 1.5.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# BioETL Dashboards v2: Usage

> **Removed 2026-07-23:** Silver Reject Explorer dashboard, Loki/Tempo Explore adjuncts, Quarantine Explorer datasource (replaced by BioETL Ops HTTP on :8000).
> Use CLI ioetl quarantine inspect for record-level forensics. See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).



Дата сверки: **2026-07-23**
Источник истины: `grafana/dashboards/*.json`

> **Surface reduction 2026-07-23:** 7 shipped dashboards (bus `0..6` only).
> Removed: Silver Reject Explorer UI, Loki/Tempo Explore adjuncts, Quarantine
> Explorer datasource. Record-level quarantine forensics → CLI
> `bioetl quarantine inspect`. Details:
> [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).

Shipped inventory (**7 dashboards**): Control Plane, Overview, Runtime, Provider
Health, Data Quality, Workflow, Alerts & SLO. Primary `0..6` refresh is `60s`.
Generic primary handoffs preserve HTTP `$run_id` for identity panels only
(not Prometheus labels).

Machine-readable navigation contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (docs/tests должны соответствовать ему).

Machine-readable selector contract: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`.

V3 baseline planning/reference surfaces:
- `docs/03-guides/dashboards/v3.0/README.md`
- `docs/03-guides/dashboards/v3.0/1-overview.md`

Human-readable selector references:
- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/selector-architecture.md`

HTTP identity backend contract:
- HTTP-backed panels (`ID`, `Processed Records`, checkpoint freshness) are
  served by **`bioetl health server`** (default Docker main: `:8000`) via
  datasource **BioETL Ops HTTP**.
- The shared above-the-fold `ID` and `Processed Records` cards on primary
  dashboards carry explicit no-value copy. Generic Grafana `No data` on those
  cards is never acceptance evidence: check `/health/live`, selector scope,
  and backend datasource errors before declaring an exact run absent or a
  zero-record state valid.
- Optional Prometheus URL for backend-side joins: `BIOETL_PROMETHEUS_URL` when set.
  Configure the URL reachable from the backend process: host/WSL runs usually
  use `http://127.0.0.1:9090`, while Docker-adjacent backends may need
  `http://host.docker.internal:9090`. Do not assume `localhost:9090` is
  universally correct when Grafana, Prometheus, and the backend run in mixed
  network namespaces.

## Какие дашборды использовать

| Dashboard                 | UID                             | Для чего                                                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 0. Trust          | `bioetl-control-plane-v1`       | Replay/resume safety: manifest, ledger, checkpoint, telemetry confidence |
| 1. Overview (Fleet)       | `bioetl-overview-v2`            | L0 answer-first Fleet: Status + Inputs evidence + First Action routes |
| 2. Pipeline Diagnostics                | `bioetl-runtime`                | Blockers, latency, telemetry gap; workflow band merged in |
| 3. Provider Health        | `bioetl-provider-health-v2`     | Population-first fleet severity + top causes |
| 4. Data Quality           | `bioetl-dq-v2`                  | Now / Run / Range lanes; quarantine aggregates |
| 5. Incident Workspace     | `bioetl-incident-v1`            | Domain-separated suspects + ALERTS timeline |
| 6. Run Explorer           | `bioetl-run-explorer-v1`        | HTTP identity + processed records (`run_id` not Prom) |
| Record forensics (CLI)    | `bioetl quarantine inspect`     | Silver structural rejects; not a Grafana board |

**Retired (not shipped):** `bioetl-workflow-overview` (→ Runtime workflow band),
`bioetl-alerts-slo` (→ Overview Alert/SLO row), `Silver Reject Explorer` UI,
`Explore Logs` / `Explore Traces` adjuncts (2026-07-23). Historical notes may still
mention `6. Alerts & SLO` / Explore Logs / Explore Traces as removed surfaces.

## From where to enter each dashboard in 1 click

| Target dashboard | 1-click entry source |
| --- | --- |
| `bioetl-control-plane-v1` | Navigation bus `0. Trust` on every other board |
| `bioetl-overview-v2` | Navigation bus `1. Overview` |
| `bioetl-runtime` | Navigation bus `2. Pipeline Diagnostics` |
| `bioetl-provider-health-v2` | Navigation bus `3. Provider Health` |
| `bioetl-dq-v2` | Navigation bus `4. Data Quality` |
| `bioetl-incident-v1` | Navigation bus `5. Incident Workspace` (or alert entry hop) |
| `bioetl-run-explorer-v1` | Navigation bus `6. Run Explorer` |
| CLI forensics | `bioetl quarantine inspect` / `bioetl run-manifest show` |

## Фильтрация

- `bioetl-overview-v2`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- `bioetl-control-plane-v1`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- `bioetl-runtime`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`, `$stage`
- `bioetl-dq-v2`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`, `$stage`
- `bioetl-provider-health-v2`: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`, `$provider`, hidden `$pipeline_context`, `$adapter`
- `bioetl-workflow-overview`: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`, `$status`, `$step_status`, `$step_kind`, hidden
  `$workflow_context`, `$pipeline_context`, `$pipeline_context_exact`,
  `$run_type_context`, `$run_type_context_exact`, `$provider_context`,
  `$provider_context_exact`
- `CLI quarantine inspect`: bounded forensic `$pipeline`, `$run_type`,
  `$reason_code`, `$field`, `$quarantine_run_id`, `$payload_hash`; it does not
  own the shared `$workflow` / `$run_id` shell
- `bioetl-alerts-slo`: `$workflow`, `$pipeline`, `$run_type`
- `bioetl-overview-v2` intentionally ships with `Workflow=All`,
  `Pipeline=All`, `Run Type=All`, and `Run ID=-` как default entry scope.
- Primary dashboards `0..5` now expose the shared context shell
  `$workflow/$pipeline/$run_type/$run_id`. `$workflow` is context/evidence
  unless the panel explicitly documents truthful intersection semantics.
- `$run_id` options on primary dashboards are loaded from
  `/ops/control-plane/filter-options` using the visible
  `$workflow/$pipeline/$run_type` context. `/ops/control-plane/selector-context`
  can resolve one coherent local selector tuple for selector-shell clients, but
  native Grafana variables do not auto-write sibling selector values.
- `bioetl-workflow-overview` uses additional hidden
  `$workflow_context/$pipeline_context_exact/$run_type_context_exact/$provider_context_exact`
  variables backed by `/ops/control-plane/filter-options?exact_run_only=1` so
  dashboard-to-dashboard links preserve exact run identity when `$run_id` is
  selected without rewriting the visible selector shell.
- Во всех non-Overview pipeline/provider dashboards `$pipeline` и `$provider`
  остаются single-select; если исходного контекста нет, используется explicit
  fallback `unknown`.
- `$run_type` всегда имеет include-all fallback; если исходного run-type
  контекста нет, используйте `Run Type=All`, а не `unknown`.
- Переходы в `3. Provider Health` из pipeline-scoped dashboards сохраняют
  `$pipeline_context` для обратного перехода и fail-close'ятся к
  `$provider=unknown`, если source scope не доказывает валидный provider label
  для target dashboard.
- Для `CLI quarantine inspect` `$pipeline` также остаётся scoped
  single-select, потому что quarantine API fail-closed требует явный
  `pipeline` параметр.
- Переменная `execution` не используется; `$quarantine_run_id` и
  `$payload_hash` остаются только в `CLI quarantine inspect`.
  `$run_id` в primary dashboards `0..5` сохраняется как HTTP-backed identity
  context для `ID`/details panels и не становится Prometheus label.
  Generic handoffs into `Silver Reject Explorer` MUST NOT map primary
  `$run_id` into `$quarantine_run_id`; forensic `quarantine_run_id` /
  `payload_hash` stay explorer/CLI concerns. Generic handoffs out of the
  explorer do not export primary `$run_id` either.

## Что смотреть в первую очередь

Policy reminder:
- every dashboard still needs one `ONE BIG QUESTION`
- first-screen scope and `First Action` remain mandatory
- provenance/risk context may stay distributed across scope panels, current
  status surfaces, descriptions and linked runbooks

State vocabulary is explicit: `OK/WARN/CRIT` are business severity;
`INCOMPLETE` means a required trust input is missing/stale; `UNKNOWN` means no
truthful verdict; `ERROR` is an explicit query/datasource/backend failure;
`VALID EMPTY`, `TELEMETRY ABSENT`, and `N/A` are neutral terminal states with
different next actions. `LOADING` is transient and cannot appear in accepted
render evidence. A blank body is never a valid state.

`bioetl-overview-v2` is the canonical frozen Overview v3 baseline. Primary
dashboards `0..5` reuse its visible context shell and common header panels:
`Provenance`, `Status`, `ID`, and `Processed Records`. Current status semantics
still belong to each dashboard role; `workflow` remains evidence context unless
documented otherwise, and `run_id` affects only the local control-plane `ID`
panel.

`Processed Records` is no longer a range-only throughput summary. It is the
shared compact stage/outcome accounting table for Bronze, Silver outcomes, and
Gold outcomes backed by local `/ops/observability/processed-records` rows over
exact-run RunLedger evidence when `$run_id` is selected, otherwise over
`bioetl_processed_records_*` recording rules and canonical
`bioetl_stage_records_total` outcomes. It intentionally omits reconciliation
status, accounted subtotal, and delta rows; missing aggregate accounting series
are diagnostic no-data/instrumentation gaps, not green zero. The table shows
`value` and formatted `percintage`: Bronze is always `100%`; `silver [valid]`
and `gold [valid]` render one decimal (`91.0%`, `90.1%`); secondary Silver and
Gold outcomes render up to three decimals with trailing zeroes trimmed
(`8.51%`, `0.47%`). Zero-valued outcome rows remain visible in the compact
table. Silver and Gold outcome percentages use Bronze total as denominator. It
formats `value` with a space as the thousands separator, left-pads shorter
values to the displayed `bronze [total]` width, and right-aligns the `value`
column. If Silver accounted rows sum below `bronze [total]`, visible Silver
rows get a red row background; if Gold accounted rows sum below `silver [valid]`,
visible Gold rows get a red row background. It does not replace the
dashboard-specific `Status` or `First Action` route.
If this table is empty, distinguish backend unavailable, no selected run/scope,
and true zero accounting rows before acting: the card links the Quarantine
Explorer health probe and monitoring setup docs for that reason.

1. `bioetl-overview-v2`, first screen (no scroll):
   `Provenance`, `Status`, `First Action`, `ID`, and `Processed Records` answer
   the L0 question: what is broken/degraded, what exact control-plane identity
   is selected or resolved, and where to open drilldown first. `OK` requires
   recent activity; missing current evidence remains `UNKNOWN`, not green zero.
   Compact current-state cards for Control Plane, Runtime, Data Quality,
   Provider, and Data Validation follow the answer band, then `Inputs` and
   `Workflow` share the final first-screen row. Firing/pending alert state lives
   immediately below in collapsed `Alert/SLO Triage`; it reads Prometheus
   `ALERTS` and is an incident triage surface, not a replacement for the
   shipped Prometheus alert rules. Historical/diagnostic evidence remains
   collapsed.
1. `bioetl-runtime`, first-screen answer area (без скролла):
   `Provenance`, `Status`, `ID`, `Processed Records`, then
   `Runtime Status`, `Runtime Blockers` и
   `First Action` отвечают на L2 current-cause вопрос и next operator move.
   `Status` is the compact shared-shell verdict; `Runtime Status` is an
   expanded first-screen mirror of the same trust-gated current-status
   recording rule next to blocker causes, not an independent second signal.
   `Metrics Evidence` is the trust precondition: non-zero scrape/rule
   health forces both verdict panels to `INCOMPLETE`; UNKNOWN also blocks zero
   counters from being treated as conclusive.
   Compact evidence row содержит `Worst Stage Lag`,
   `Monitor Runtime Blockers`, `Runtime Error Rate`,
   `Metrics Evidence` и `Failed Runs`; selected-range risk
   markers не определяют current status and render neutral zero evidence
   instead of green OK cards. Non-zero/UNKNOWN telemetry gap делает zero-count
   cards недоказательными.
   Datasource trust markers are targeted: `Runtime` keeps this explicit
   telemetry-gap panel first-screen, `Control Plane` uses
   `Inspect: Telemetry Missing`, while `Silver Reject Explorer` relies on
   explicit no-data/backend-failure copy instead of a generic datasource-health
   stat tile.
1. `bioetl-runtime`, row-группы по сценарию:
   `Detect`, `Localize`, `Escalate` are all collapsed by default. Optional
   `Tracing-only Log Hygiene` is collapsed because Loki/Tempo are tracing-profile
   evidence, not first-pass runtime health. Открывайте ровно одну нужную
   группу после чтения answer row и selected-range KPI, чтобы сократить шум
   первого экрана.
1. `bioetl-control-plane-v1`, answer row:
   `Provenance`, `Status`, `ID`, `Processed Records`, then
   `Monitor: Replay Safety State`, `Monitor: Checkpoint Freshness Lag (seconds)`,
   `Monitor: Manifest / Ledger Integrity` и `Inspect: Telemetry Missing`
   отвечают на L1/L2 вопрос: можно ли доверять
   manifest/ledger/checkpoint/lineage state и безопасно выполнять
   replay/resume прямо сейчас. Headline `Status` reads
   `bioetl_control_plane_current_status_trusted`: `OK` requires complete replay,
   checkpoint, manifest/ledger, and telemetry evidence; missing/stale evidence
   is `INCOMPLETE`. Любой non-zero current-signal требует расследования до
   replay/resume; non-zero/UNKNOWN telemetry-missing risk означает, что зелёные
   нули нельзя считать доказательством безопасности. `Track: Replay / Resume Blockers in Range`
   и `Inspect: Terminal Run Events by Status in Range` вынесены ниже как
   selected-range evidence, а не first-screen verdict. Replay/checkpoint
  runbook path здесь canonical через `checkpoint-debugging.md`; compact
  manifest/run identity remains in the shared `ID` panel, while deeper
  P0/P1/P2 anchors, replay parentage, composite identity, checkpoint
  current-vs-persisted anchor compare, identity gaps, and copy-friendly full
   values live in the collapsed `Identity evidence and remaining replay-safety
  signals` row backed by `/ops/control-plane/identity-evidence`.
1. `bioetl-provider-health-v2`, first-screen GLOBAL answer row:
   `GLOBAL Provider Scope`, `Monitor GLOBAL Provider Severity Matrix`,
   `Inspect Critical Providers`, `Inspect Provider Top Causes`,
   `Monitor Provider Telemetry Freshness` и `First Action`
   отвечают на вопрос «какой provider degraded/failing и почему». Panel `id=114`
   (`Review Raw Provider Health Enum`) остаётся raw source enum
   (`0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`) ниже first screen как evidence.
  `Monitor Provider Telemetry Freshness` отделяет empty severity matrix от
  telemetry gap: если в активном Grafana range нет ни
  `bioetl_provider_current_status`, ни
  `bioetl_provider_range_operational_ok`, это не healthy state.
  `bioetl_provider_range_operational_ok` является 12h operational-evidence
  projection: successful provider activity in range can move `Status` to `OK`
  without claiming that the selected pipeline run succeeded. Provider Health
  remains provider-first; `$workflow/$pipeline/$run_type/$run_id` are shared
  shell context for HTTP identity/accounting cards, and `$run_id` must not be
  introduced into Provider Health PromQL. `Status` is selected-provider scope
  and renders as supporting scoped evidence rather than the visual owner of the
  fleet answer; `Monitor GLOBAL Provider Severity Matrix`,
  `Inspect Critical Providers`, and `Inspect Provider Top Causes` are GLOBAL
  fleet posture and may disagree by design. Shared `ID` и `Processed Records`
  cards на том же first screen остаются bounded pipeline-context evidence и не
  доказывают current provider health. `First Action` spells out this read order:
  GLOBAL severity, telemetry freshness, critical providers/top causes, then
  selected-provider supporting evidence. `Inspect Provider Top Causes` может
  оставаться
   непустой даже при `GLOBAL severity = OK`, потому что canonical cause
   projection включает early-warning provider signals независимо от
   current-status projection; это diagnostic lead, а не самостоятельное
   доказательство current non-OK severity. Если status остаётся non-OK, а
   canonical cause projection пуста, `Inspect Provider Top Causes` остаётся
   empty table; это explainability gap, а не healthy state. В таком случае
   расследование нужно продолжать по severity matrix и optional provider
   diagnostics, а не трактовать пустую таблицу как отсутствие инцидента.
   Optional latency, adapter, rate-limit, and circuit-breaker panels remain
   collapsed under `Selected Provider Detail`; no-data
   in those panels does not refute current provider severity and should not
   dominate the first-screen verdict path.
   `First Action` is the bounded CTA surface for this dashboard: review the
   severity matrix, inspect critical providers, or inspect provider top causes
   before leaving the page.
1. `bioetl-dq-v2`, first-screen answer row:
   `Monitor DQ Current Status`, `Now · DQ Threshold State`,
   `Now · DQ Current Reasons` и `Review: First Action`
   отвечают на вопрос «DQ сейчас OK/WARN/CRIT/UNKNOWN и какое действие
   первое». `Status` is the compact shared-shell verdict; `Monitor DQ Current
   Status` is an expanded first-screen mirror beside threshold/reason
   explainability, not an independent second signal. Сразу под answer row
   расположен compact band labelled as TIME RANGE:
   `Monitor: Data Quality Score (Volume-weighted)`,
   `Monitor: Worst-Entity DQ Score`, `Time Range · Worst Freshness Age (hours;
   SLA 24/72)`, `Range · Records Quarantined`, `Track: Silver Filter
   Rejects in Range`, and `Track: DQ Blocked Records in Range (Evidence)`.
   Freshness query output, display unit, and thresholds all use hours: WARN at
   `24h`, CRIT at `72h`. `Track Range Evidence: Bronze -> Silver -> Gold` lives
   inside collapsed diagnostics as deeper selected-range evidence. Это
   pipeline-wide snapshot; `$run_type` and stage filters below control only
   selected-range evidence.
   `Review: First Action` stays the canonical DQ CTA: review current status,
   inspect current reasons, or open `Silver Reject Explorer` without leaking
   unsupported workflow/provider scope.
1. `bioetl-overview-v2`, routing and evidence rows:
   `Control Plane`, `Runtime`, `Data Quality`, `Provider`,
   `Data Validation`, `Inputs`, и `Workflow` показывают current-only operator
   state с явным scope. Status tables use row-wide threshold coloring, а не
   только окраску ячейки `Status`. Compact historical trend/evidence panels
   вынесены ниже первого экрана в collapsed `L1 Historical Trends` и
   `Range Evidence`; они служат selected-range/L1 evidence и не определяют
   `Status` или `First Action`. `Diagnostics & Docs` содержит routing по
   logs/traces/raw metrics.
1. `bioetl-workflow-overview`, panels `id=2`, `id=3`, `id=6`, `id=7`, `id=4`,
   `id=5`, `id=8`:
   selected-range declarative workflow evidence for failed runs, failed/skipped
   step events, run-outcome mix, step outcomes, и step latency. Используйте его,
   когда нужен bounded workflow evidence layer. Shared `run_id` помогает
   identity lookup в `ID`, но current stage, replay/resume или provider/DQ root
   cause остаются задачами соседних dashboards.

## Incident first steps (Runtime top navigation)

В `2. Pipeline Diagnostics` cross-dashboard routing выполняется через полный top-level bus:
`0. Trust`, `1. Overview`, `2. Pipeline Diagnostics`, `3. Provider Health`,
`4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`, затем
`0..6` bus only (adjuncts removed); текущий Runtime item
остаётся видимым disabled.

Panel-level dashboard handoffs и `First Action` dashboard CTAs намеренно
отсутствуют, чтобы не создавать второй путь в тот же target dashboard. Для
быстрого старта triage сначала выберите домен инцидента через top-level bus,
затем используйте detail/condition cards внутри выбранного dashboard.



### Screenshot map: `bioetl-overview-v2` (новая структура первого экрана)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Provenance                                                      │ Status      │
├──────────────────────┬──────────────┬────────────────────────────────────────┤
│ ID                   │ Processed    │ First Action                           │
│                      │ Records      │                                        │
├──────────────┬───────┬──────────────┬──────────┬─────────────────────────────┤
│ Control Plane│ Runtime│ Data Quality │ Provider │ Data Validation             │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ Inputs: deviation-first matrix       │ Workflow: current-state matrix        │
├──────────────────────────────────────┴───────────────────────────────────────┤
│ ▸ Alert/SLO Triage: actual ALERTS evidence                                   │
│ ▸ L1 Historical Trends                                                       │
│ ▸ Range Evidence                                                             │
│ ▸ Diagnostics & Docs                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

Первый экран без скролла должен отвечать на вопрос **«что сломано и куда идти дальше»**:
- что сломано: `Status` + compact L1 current-state cards + deviation-first
  `Inputs` / `Workflow`; `Triage Alert State` раскрывается после первичного
  narrowing, когда нужен alert-level context;
- куда идти дальше: `First Action` с `action_target/action_reason/action_dashboard_uid`;
- какая execution identity выбрана: `ID`, backed by local control-plane manifests;
- что было в окне времени: collapsed `L1 Historical Trends` и `Range Evidence`;
- где искать сырые traces/logs/metrics: collapsed `Diagnostics & Docs`.

Compact evidence ниже первого экрана:
- `Runtime Blockers Trend` (`id=9018`): selected-range L1 runtime evidence over
  `bioetl_l1_runtime_blocker_status`; no-data/gaps остаются diagnostic, а не
  OK; handoff `Open Runtime`.
- `DQ Status Trend` (`id=9019`): selected-range L1 Data Quality evidence over
  `bioetl_l1_dq_status`; missing series не доказывает green state; handoff
  `Open Data Quality`.
- `Gold Lifecycle Trend` (`id=9020`): selected-range L1 data-validation
  lifecycle evidence over `bioetl_l1_gold_lifecycle_status` with
  `lifecycle_state`; disabled Gold stage may be OK, but missing series is still
  diagnostic. Contract-excluded Gold records (`outcome="excluded_by_contract"`)
  are terminal lifecycle evidence via `lifecycle_state="terminal_contract_excluded"`;
  handoffs `Open Runtime` and `Open Control Plane`.
- `Historical Failures` (`id=9010`): selected-range historical failure table
  over `bioetl_pipeline_runs_total`; zero matching rows only means no failed-run
  samples in the selected range, not current OK; handoff `Open Runtime`.
- `Recent Terminal Runs` (`id=9011`): selected-range non-success terminal-run
  table over `bioetl_pipeline_runs_total`; no terminal rows is not proof of
  current OK; handoffs `Open Control Plane` and `Open Runtime`.

Эти пять panels retained intentionally. Current verdict по-прежнему определяется
только first-screen `Status`, `First Action`, `Inputs` и current L1 cards.
## Silver Filter Rejects workflow

- Для быстрых summary используйте `Silver Rejects + Rate` в
  `bioetl-overview-v2` и `Range · Silver Filter Rejects` в `bioetl-runtime`. Overview
  intentionally не показывает standalone green reject-rate gauge: rate
  интерпретируется только рядом с Bronze denominator / activity context.
- `bioetl-overview-v2` и `bioetl-runtime` содержат явный handoff в
  `4. Data Quality`, но runtime dashboard больше не тащит в себя DQ internals:
  он показывает только compact handoff conditions.
- Для current-state narrowing используйте `Now · DQ Current Reasons`; для
  bounded cause summary используйте `Inspect: Top Silver Reject Reasons (Pareto)` и
  `Inspect: Top Silver Reject Fields` в collapsed-by-default rows
  `bioetl-dq-v2` (раскройте их для расследования).
  `Inspect: Silver Filter Rejects by Pipeline` остаётся scope/distribution panel
  по stage-total `filtered_out`, а не reason drilldown.
- Маршрут triage: **L1 summary -> L2 explorer**.
  1. **L1 summary:** начните с `4. Data Quality` (first-screen current status,
     threshold state, reasons, invalid-record-policy note), чтобы определить
     severity и первое действие.
  1. **L1 cause narrowing:** раскройте collapsed-by-default rows `Silver Structural / Gold Contract-Semantic Rejects` и `Validation Failures / Runtime Diagnostics / Trends`. В reject row сначала проверьте trust guard `Monitor: Silver Filter Reject Accounting Mismatch`, затем `Inspect: Top Silver Reject Reasons (Pareto)` / `Inspect: Top Silver Reject Fields`, и только после этого переходите к pipeline distribution через `Inspect: Silver Filter Rejects by Pipeline`.
  1. **L2 explorer:** откройте `Silver Reject Explorer` через top-level link в `4. Data Quality` для Silver structural record-level списка, выбора `reason_code/field/quarantine_run_id` и detail по `payload_hash`. Для Gold contract/semantic rejects используйте Gold reject panel в `4. Data Quality`; `FILTERED_OUT_SILVER` является legacy alias только для Silver structural rejects.
  1. **L2 no-data gate:** считайте `0` rejects нормой только когда `Review: First Action / No-Data Semantics` подтверждает конкретный pipeline, доступный BioETL Ops HTTP и ненулевой Bronze denominator; zero-reject workflow run is a valid empty explorer state only after those checks pass. Zero matching rows остаются empty-result состоянием, а plugin errors, unsupported filter chains, `unknown` pipeline или `bronze_records=0` остаются UNKNOWN/error.
  1. Используйте quarantine CLI для action-операций (`replay/resolve/purge`) и финального подтверждения remediation.
- Эти панели отвечают на вопросы:
  - растёт ли объём `filtered_out`;
  - в каком `$pipeline` проблема сильнее;
  - это локальный всплеск или устойчивый тренд в выбранном time range;
  - какие `reason_code` и `field` сейчас доминируют в bounded dashboard summary.
- Для action-перехода из explorer в CLI используйте:
  ```bash
  bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --run-id <run-id> --limit 200
  bioetl quarantine resolve --pipeline <pipeline> --payload-hash <payload-hash> --status IGNORED
  ```
- Grafana в shipped конфигурации разделена по ролям:
  `1-4` dashboards дают summary/trend и bounded breakdown на Prometheus.
  `Silver Reject Explorer` даёт row-level browsing через datasource `BioETL Ops HTTP`.
- Record-level drilldown больше не ограничен только CLI.
  CLI остаётся execution surface для replay/resolve/purge.


## Unified Top Navigation CTA (v2)

Primary dashboards MUST follow the canonical navigation contract in
`navigation-contract.md` and the machine-readable
`contracts/navigation-links.yaml`.

The top-level dashboard bus is:
`0. Trust`, `1. Overview`, `2. Pipeline Diagnostics`, `3. Provider Health`,
`4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`. Each page renders the full
visual bus in navigation panel `id=1000`; the current dashboard stays visible
as a disabled high-contrast item, while machine-readable `panel.links` still
omit self-links.
The canonical shipped surface is navigation panel `id=1000`, so
`dashboard.links[]` does not need to duplicate the same bus next to Grafana
variables. Any duplicate dashboard-to-dashboard link from one dashboard to the
same target dashboard is forbidden.

Every shipped navigation panel `id=1000` exposes global adjunct links
`Silver Reject Explorer`, `Explore Logs`, and `Explore Traces` after bus
`0..6`. Composition and order are identical on all eight dashboards. The
theme-safe bus uses solid contrast tokens and wraps at `1024px`, so links do not
clip or disappear in light mode. These links open in the same window.
`Explore Logs` is a baseline-first adjunct surface: zero lines can legitimately
mean Loki shipping is disabled, no BioETL streams were shipped in range, or the
operator still needs to refine scope inside Explore.
`Explore Traces` is a traced-run-only adjunct surface; if the runtime used
`NoOpTracing`, empty Tempo results are expected rather than a dashboard defect.
Shipped trace handoff opens the explicit search-first Tempo route, preserves
the active dashboard range via `${__from}` / `${__to}`, pins a safe default
`groupBy=resource.service.name`, and keeps stable pipeline/provider TraceQL
scope, so Tempo metrics queries stay under the local limit and `All` run-type
selectors do not collapse into an empty regex before the operator changes
grouping.

Variable handoff policy for dashboard links remains strict and bounded:

- `includeVars=false` for every link (no implicit variable leakage).
- Pass only target-scoped variables directly in URL (`var-*`) when required by the destination dashboard.
- For primary operator dashboards pass the shared shell explicitly as
  `workflow/pipeline/run_type` plus preserved identity `run_id`; Silver
  Explorer remains a bounded exception and receives only `pipeline/run_type`.
- For provider flow pass `provider/pipeline_context` plus the shared shell;
  `adapter` remains detail-only and may fall back to its target default.
- Workflow-specific state variables (`$status`, `$step_status`, `$step_kind`)
  and forensic IDs (`$quarantine_run_id`, `$payload_hash`) MUST NOT be
  propagated into non-target dashboards. Primary `$run_id` is allowed only
  between primary dashboards that expose the same selector. `$workflow` may
  appear as shared context, but links still pass only target-scoped variables
  explicitly.
- Top-level links дополнительно маркируются приоритетом (`primary`, `secondary`, `contextual`) через contract block `top_level_link_priority_by_uid`; приоритет должен быть виден в `title`/`tooltip` для неоднозначных маршрутов.

## Default dashboard windows (L0/L1 baseline + L2 forensic exception)

- Единый baseline для operator-facing L0/L1 dashboards:
  - `overview`, `runtime`, `dq`, `control-plane`, `workflow-overview` -> `time.from=now-12h`, `refresh=60s`.
- Forensic L2 exception:
  - `silver-reject-explorer` -> `time.from=now-24h`, `refresh=1m`.
  - Justification: forensic-поиск по reject payload обычно начинается с более широкого окна и не требует 30s polling; более медленный refresh снижает ненужные перезапросы при row-level drilldown.
- Любое отклонение от baseline MUST сопровождаться явным обоснованием в документации и в PR (почему это не L0/L1 operator window).
- Machine-readable contract source: `docs/03-guides/dashboards/contracts/navigation-links.yaml` -> `default_time_refresh_policy` + `default_time_refresh_policy_exceptions` (for explicit, justified deviations).


## Drilldown

- `bioetl-overview-v2`: L0 Overview отвечает на один primary question:
  what is currently broken, warning, or unknown in BioETL, and where should the
  operator drill down first? Top-level dashboard links follow the `0..6` bus
  and do not duplicate panel-level dashboard links.
  Cross-dashboard URLs передают только target-scoped variables; provider/workflow
  dashboards не наследуют unsupported selector leakage. `Status` and
  `First Action` are the first operator answer and both stay in the selected
  `$pipeline/$run_type` scope; subsystem cards preserve explicit drilldown links.

## First 2 clicks scenario (operator)

1. **Click #1:** открыть `bioetl-overview-v2`, прочитать `Status` + `First Action`.
2. **Click #2:** открыть рекомендуемый dashboard из top-level bus (`0. Trust`, `2. Pipeline Diagnostics`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`).

Цель сценария: root-cause направление должно быть определено максимум за 2 клика без обязательной прокрутки по нечастым CTA.
- `bioetl-runtime`: top-level links `0. Trust`, `1. Overview`,
  `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`,
  `0..6` bus only (adjuncts removed) дают явный
  routing path из L2 runtime triage. Cross-dashboard handoffs передают только
  target-scoped variables; forensic IDs в runtime dashboard запрещены.
- `bioetl-control-plane-v1`: `0. Trust` отвечает на один
  primary question: can we trust manifest/ledger/checkpoint/lineage state and
  safely replay/resume? Cross-dashboard routing is handled only by the top-level
  bus; panel-level dashboard handoffs are intentionally absent.
  Переход в `3. Provider Health` передаёт `provider=unknown` и
  `pipeline_context=$pipeline`; `adapter` не передаётся, чтобы target dashboard
  использовал собственный fallback `All adapters`.
  First-screen current-status cards normalize a manually selected
  `workflow_<pipeline>` value back to the entity pipeline before reading
  current-state recording rules, so `workflow_chembl_assay` resolves to the
  same trust verdict as `chembl_assay`.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-control-plane-v1`, проверить `Monitor: Replay Safety State` (`id=891`), `Inspect: Telemetry Missing` (`id=907`) и `Next Action: Replay Diagnostics` (`id=906`).
  2. Click #2: перейти через top-level bus в `2. Pipeline Diagnostics` (если есть активный blocker) или `4. Data Quality` (если blocker связан с downstream quality symptoms). На первом экране оставлены current-status Trust KPI: `id=891..893`, `id=907`, copyable identity anchors and единый CTA `id=906`; `Track: Replay / Resume Blockers in Range` (`id=130`) живёт внутри первого collapsed replay/checkpoint row, а `Inspect: Terminal Run Events by Status in Range` (`id=908`) остаётся manifest/ledger range evidence.
  Все остальные control-plane метрики перенесены в collapsed incident rows.
  Рекомендованный operator path: сначала проверить blocker cards, затем открыть
  ровно один collapsed diagnostic row под конкретный incident-pattern.
  Порядок row-блоков стандартизирован по частоте инцидентов: `Checkpoint/Replay`
  -> `Manifest/Ledger` -> `Global Control Plane` -> `Audit/Lineage` ->
  `Known Missing Signals`. GLOBAL read-path panels не
  фильтруются по `$pipeline/$run_type`; это сознательно, потому что
  `bioetl_control_plane_reads_total` и
  `bioetl_control_plane_read_duration_seconds_bucket` глобальны по
  `store/operation/status`.
- `bioetl-provider-health-v2`: dashboard links `0. Trust`,
  `1. Overview`, `2. Pipeline Diagnostics`, `4. Data Quality`, `5. Workflow` дают быстрый
  переход из provider health surface без дублирования Runtime variants.
  Panel `id=114` (`Review Raw Provider Health Enum`) показывает явный enum
  raw-source mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY` as below-fold
  evidence, while canonical first-screen severity remains `Status` plus
  `Monitor GLOBAL Provider Severity Matrix`. Panel `id=9104`
  (`Monitor Provider Telemetry Freshness`) is the first-screen trust marker:
  missing `bioetl_provider_current_status` samples in the active Grafana time range mean telemetry
  gap, not proof that providers are healthy. Raw status stays fail-closed
  `UNKNOWN`, если provider universe существует, а raw status sample отсутствует.
  Operational OK over the default 12h range is backed by
  `bioetl_provider_range_operational_ok`; it is provider activity evidence
  only and never adds `$run_id` to provider PromQL.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-provider-health-v2`, проверить `Monitor GLOBAL Provider Severity Matrix` (`id=9101`), `Inspect Critical Providers` (`id=9102`), `Inspect Provider Top Causes` (`id=9103`) и `Monitor Provider Telemetry Freshness` (`id=9104`).
  2. Click #2: перейти в `2. Pipeline Diagnostics` при active degradation/failure trend или
     в `0. Trust` при симптомах retry exhaustion/state inconsistency.
- `bioetl-dq-v2`: dashboard links `0. Trust`, `1. Overview`,
  `2. Pipeline Diagnostics`, `3. Provider Health`, `5. Workflow`, `Silver Reject Explorer`,
  `Explore Logs`, `Explore Traces` дают переходы для DQ incidents и freshness
  investigation. `Explore Traces` здесь остаётся traced-run-only adjunct;
  включайте tracing через `--tracing` или
  `BIOETL_OBSERVABILITY__TRACING_ENABLED=true`, если ожидаете Tempo evidence.
  Handoff в Explorer передаёт только bounded `$pipeline/$run_type`
  scope, а не generic `includeVars` leakage.
- `CLI quarantine inspect`: dashboard bus links `0..6` plus global
  adjunct links `Explore Logs` и `Explore Traces`; self-link to
  `Silver Reject Explorer` intentionally omitted. Main table поддерживает data
  links для self-drilldown по `payload_hash` и CLI handoff; self-drilldown
  stays same-tab, while `data:text/plain` CLI links open in a new tab. Верхняя
  explanatory panel явно показывает banner `default 24h forensic window`,
  чтобы оператор не интерпретировал explorer как обычное `now-12h` окно.

### Expected operator behavior for DQ -> Explorer handoff

- Любой pipeline-scoped dashboard handoff в `Silver Reject Explorer` передаёт
  только `$pipeline/$run_type`, а provider/workflow surfaces fail-close'ятся к
  bounded defaults. Explorer intentionally открывает более широкое окно
  `now-24h` (forensic default) для редких инцидентов и sparse reject events.
- `Inspect: Top Silver Reject Reasons (Pareto)` и `Inspect: Top Silver Reject Fields` intentionally не
  дублируют второй dashboard-to-dashboard handoff: оператор использует их как
  bounded cause summary, затем переходит в top-level `Silver Reject Explorer`.
- `Inspect: Silver Filter Rejects by Pipeline`, `Inspect: Top Silver Reject Reasons (Pareto)`,
  `Inspect: Top Silver Reject Fields`, `Inspect: Quarantine by Error Type` и
  `Track: Anomalies Detected` теперь сохраняют honest empty-state semantics:
  при отсутствии событий в выбранном окне они остаются пустыми и не создают
  synthetic buckets вроде `no_events` / `none`.
- `Inspect: Quarantine by Error Type` intentionally shipped as horizontal
  `bargauge`, not `piechart`: для quarantine/error family triage важнее
  сравнение категорий, чем композиционная доля slices.
- Оператор SHOULD сначала подтвердить, что текущий spike/аномалия видны в
  summary-панелях DQ (`Top Silver Reject Reasons/Fields`) и только затем делать
  record-level drilldown в Explorer.
- После перехода оператор SHOULD проверить explanatory banner
  `default 24h forensic window`; при шуме или слишком большом объёме данных
  окно можно сузить вручную до operational range.
- Для очень редких инцидентов оператор MAY оставить 24h окно и уточнить
  контекст через `reason_code`, `field`, `quarantine_run_id` и `payload_hash` перед
  action-операциями в CLI.
- `bioetl-workflow-overview`: dashboard links `0. Trust`,
  `1. Overview`, `2. Pipeline Diagnostics`, `3. Provider Health`, `4. Data Quality`;
  cross-dashboard handoffs preserve primary `$run_id` but do not leak
  `$status/$step_status/$step_kind` into non-workflow targets.
- `bioetl-workflow-overview`: first screen keeps `Failed Workflow Runs / Range`,
  `Failed Pipeline Steps / Range`, `Failed Transform Steps / Range`,
  `Skipped Step Events / Range`, `Workflow Run Outcomes / Range`, and
  `First Action`; zero counters render neutral `0 · valid empty range`, while
  `Workflow Run Outcomes / Range` distinguishes `VALID EMPTY`, `NO MATCHING
  SCOPE`, `TELEMETRY ABSENT`, and `ERROR / UNKNOWN`. Deeper step evidence lives
  under collapsed row `Step Diagnostics` with
  `Step Outcomes by Kind / Step Status / Range` and
  `Step Duration p95 by Kind / Step Status / Range`.
- `bioetl-workflow-overview`: `First Action` is the only justified
  panel-level handoff exception. Although the header bus already exists, this
  panel remains the sole first-screen workflow CTA and therefore exposes
  bounded `Open ...` dataLinks to neighboring dashboards while preserving the
  time range and resetting unsupported workflow-only state filters.
- `CLI quarantine inspect`: `Review: First Action / No-Data Semantics`
  now also carries bounded CTA row links (`Review total rejects`,
  `Review scoped summary`, `Open Data Quality`) so the first-screen forensic
  interpretation panel remains actionable without leaking `quarantine_run_id` or
  `payload_hash` into cross-dashboard handoffs.
  The visual sequence is scope → `Monitor Explorer Backend Health` → one action
  → summary → top causes. `Trends · expand when rejects exist` and `Records and
  selected detail · expand after narrowing` remain collapsed until relevant.
  Backend Health must terminate as healthy, explicit error, or valid empty;
  blank/loading and error + `No data` contradictions fail render evidence.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-workflow-overview`, проверить `Failed Workflow Runs / Range` (`id=2`), `Failed Pipeline Steps / Range` (`id=3`) и `Failed Transform Steps / Range` (`id=6`).
  2. Click #2: перейти в `2. Pipeline Diagnostics` для incident triage по pipeline impact, в `4. Data Quality` для transform/filtering fallout, или в `0. Trust` для replay/resume trust verification. Workflow Prometheus evidence uses bounded workflow labels and never requires `run_id`/`step_id` labels; shared `$pipeline/$run_type/$run_id` context feeds only context/identity surfaces unless a panel documents otherwise.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: pipeline-scoped
  dashboards предварительно фильтруют TraceQL по `span."bioetl.pipeline"`, а
  provider dashboard — по `span."bioetl.provider"`. Runtime handoff does not
  ship `run_type` in TraceQL because `$run_type` is include-all/multi-select.
  Это не заменяет
  correlation по `trace_id` /
  `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом
  клике.
- `bioetl-runtime` row `Tracing-only Log Hygiene` содержит Loki-backed panels
  `Inspect Warning Logs`, `Inspect GLOBAL Unstructured Logs`,
  `Inspect Top Warning Events by Event / Logger / Range` и
  `Track GLOBAL Log Hygiene Trend`. Это optional tracing-profile evidence, а
  не first-screen status; row collapsed by default in the canonical dashboard
  to avoid datasource warning noise when the optional tracing profile is not
  enabled. Panels `#250`, `#251` и `#257` используют bounded one-hour lookback
  независимо от более широкого активного Grafana time range; trend panel
  `#258` продолжает использовать активный time range;
  unstructured parser-error panel intentionally renders parsed `.__error__`;
  Prometheus condition-summary panels в runtime используют shipped fixed-window
  recording rules и не зависят от `$__range`; freshness handoff is explicitly
  raw lagged-entity evidence, not a runtime alert-condition recording rule.

- Runtime escalation triage path:
  `Monitor Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `Inspect DQ Alert Conditions` / `Inspect Freshness Lagged Entities >24h` -> `dq-failure-investigation.md`,
  `Inspect Control-plane Alert Conditions` -> `run-manifest-inspection.md`,
  `Inspect GLOBAL Provider Alert Conditions` -> `incident-response.md`,
  `Monitor No-Records Runs` -> `checkpoint-debugging.md`.
  `0` на этих handoff cards допустим только когда selected runtime
  `pipeline/run_type` universe или GLOBAL provider current-status telemetry
  существует; отсутствующий scope остаётся `UNKNOWN`, а не synthetic OK.

- Known missing runtime panels:
  `Retry vs Failure` и `Batch Size Distribution` не shipped, пока repo не
  подтверждает bounded runtime metric family для этих решений.

## Важные пороги (из JSON)

- `overview.id=214 (Status)`: `CRIT` при runtime blocker `>0`, DQ hard fail `>0`, blocking data-validation lifecycle или control-plane blocker `>0`; `WARN` при non-fatal warning-only сигналах; `UNKNOWN` при no recent samples. Panel links route directly to Runtime / Control Plane / Data Quality / Provider Health / Workflow with the current time range.
- `overview.id=215 (First Action)`: priority order `Runtime > Control Plane > Gold Lifecycle > DQ > Provider > Workflow > Monitor`. If the selected scope is missing from `bioetl_overview_pipeline_run_type_universe` (aliased from the runtime pipeline/run_type universe), the panel falls back to `NO_ROUTE` instead of rendering empty. Next action: open the first non-OK surface via the matching panel link. Runtime / Control Plane / DQ / Workflow handoffs preserve `workflow/pipeline/run_type/run_id`; Provider Health fail-closes to `provider=unknown` while preserving `pipeline_context`; workflow-only state filters are not propagated.
- `overview` first-screen selected-scope cards normalize a manually selected `workflow_<pipeline>` value back to the entity pipeline before reading `bioetl_l0_*` / `bioetl_l1_*` summary recording rules. For example, `workflow_chembl_assay` resolves to the same current-state summary rows as `chembl_assay`.
- `dq.id=2 (DQ Score Snapshot)`: no-data остается `UNKNOWN`, не `0`; hard-fail signals блокируют promotion, warning-only означает drift. Next action: hard-fail -> reject/quarantine diagnostics; warning-only -> trend + top reasons.
- `overview.id=9002 (Inputs)`: использует `max by (input) (bioetl_l0_input_status_selected{pipeline=~"$pipeline",run_type=~"$run_type"})`. Это compact projected selected-scope surface: first-screen таблица держит одну worst-status строку на operator input, чтобы не требовать scroll на default `Workflow=All/Pipeline=All/Run Type=All`.
- `dq.id=154 (Blocked Share Trend)`: numerator = `filtered_out + quarantined`,
  denominator = Bronze input in the same window. Sustained growth = filter /
  quarantine pressure, spike = incident. Next action: `Top Silver Reject
  Reasons` + `Silver Reject Explorer`/quarantine CLI.
- `runtime.id=16 (Monitor Runtime Blockers)`: non-zero = active blocker count; `UNKNOWN` means missing current runtime status/blocker telemetry and must not be treated as OK. Next action: runtime blockers table + culprit stage panels, затем logs/traces при необходимости.
- `runtime.id=9102 (Metrics Evidence)`: `0=SCRAPING/RULES OK`, `1=SCRAPE/RULE GAP`, `>=2=SCRAPE+RULE GAP`, `null=UNKNOWN`; checks scrape health plus runtime dashboard recording-rule evaluation failures, rule-group presence, and rule-group freshness. Any non-zero value forces headline `Status` and `Runtime Status` to `INCOMPLETE` (`3`).
- `runtime.id=205/id=236 (Failed Runs / Monitor No-Records Runs)`: `0` is valid only when `bioetl_runtime_pipeline_run_type_universe` confirms the selected scope; missing selected scope remains `UNKNOWN`.
- `runtime.id=220 (Runtime Error Rate)`: elevated ratio with meaningful 30m Bronze denominator (`>=20`) = degradation risk; WARN starts at 5%, dashboard CRIT escalation at 20%, and lower/missing denominator stays `UNKNOWN`. Next action: `Inspect Errors by Stage / Error Code / Range` + failed runs/backlog/lag panels.
- `runtime` current-triage panels normalize a manually selected `workflow_<pipeline>` value back to the entity pipeline before reading current runtime recording rules and error-rate/lag evidence. For example, `workflow_chembl_assay` resolves to the same current status and blocker scope as `chembl_assay`; `UNKNOWN` on error-rate still remains valid when the 30m Bronze denominator is absent or `<20`.
- `control-plane.id=9401 (Status)`: `0=OK`, `1=WARN`, `2=CRIT`,
  `3=INCOMPLETE`, `null=UNKNOWN`; it reads
  `bioetl_control_plane_current_status_trusted`, so missing/stale checkpoint or
  required telemetry evidence blocks replay/resume approval.
- `control-plane.id=907 (Inspect: Telemetry Missing)`: `0=OK`, `1=WARN`, `>=2=CRIT`, `null=UNKNOWN`; non-zero/UNKNOWN means validate scrape/rules before trusting blocker zeros.
- `control-plane.id=130 (Track: Replay / Resume Blockers in Range)`: selected-range blocker count across manifest writes, ledger appends, checkpoint compatibility, replay reconstructability, replay drift, and lineage refs. Любой non-zero value означает investigate before replay/resume, но это historical range evidence, а не first-screen current-status verdict.

- `overview.Status`: `CRIT` при failed runs `>0`, stage backlog `>0`,
  worst lag `>=300s`, DQ hard fail `>0` или control-plane blocker `>0`;
  `WARN` при warning-сигналах provider/DQ/freshness/workflow или
  pending-gold conditions; `UNKNOWN`
  при отсутствии recent activity/samples; `OK` только при recent activity и
  отсутствии blockers/warnings. Panel-level links duplicate the canonical
  Runtime / Control Plane / Data Quality / Provider Health / Workflow bus for
  first-click triage.
- `overview.First Action`: runtime имеет приоритет над control-plane,
  blocking gold lifecycle, DQ, provider и workflow; row
  `action_target/action_reason/action_dashboard_uid`
  replaces the old opaque severity-only handoff. `NO_ROUTE` means the selected
  `pipeline/run_type` scope is not present in the overview universe and should
  be validated before deeper drilldown. Panel data links preserve the same
  time range and provide explicit operator handoff even when the next-action route
  itself resolves to `MONITOR`.
- `overview.Data Validation`: first-screen table now aggregates the worst
  current gold lifecycle status by `pipeline` across the selected `run_type`
  scope. Exact `lifecycle_state` detail remains available in Runtime / trend
  surfaces; contract-excluded Gold records are treated as terminal OK evidence,
  not missing Gold. The Overview card stays compact so it does not require
  scroll.
- `overview.Workflow`: workflow summary is
  projected from `bioetl_workflow_runs_total` via fixed-window
  `max_over_time(...)` evidence so short-lived successful workflow runs remain
  visible after the CLI process exits. `UNKNOWN` is valid only when the
  selected scope has no recent workflow evidence at all.
- `overview.Recent Terminal Runs`: range-evidence table now
  shows only non-success terminal statuses grouped by `pipeline/status`; success
  completions are intentionally omitted because they create scroll without
  improving first-click triage.
- `control-plane.Track: Replay / Resume Blockers in Range`: selected-range blocker
  count. Нулевое значение само по себе не доказывает safety; его нужно читать
  вместе с current trust cards и `Inspect: Telemetry Missing = 0`.
- `control-plane.Inspect: Terminal Run Events by Status in Range`: selected-range
  terminal evidence grouped by `terminal_status`. Эта панель pipeline-scoped only:
  metric contract не несёт `run_type`, поэтому `run_type` selector здесь не
  влияет на breakdown.
- `control-plane.Manifest/Ledger Failure Ratio Severity`: severity projection за
  фиксированное окно `30m`: `0=OK`, `1=WARN` при `>0`, `2=CRIT` при `>0.10`.
- `control-plane.Monitor: GLOBAL Control-Plane Read Failure Ratio Severity`: severity
  projection за фиксированное окно `30m`: `0=OK` при `<=5%`, `1=WARN` при `>5%`,
  `2=CRIT` при `>10%`.
- `control-plane latency p50/p95/p99`: histogram-backed panels сохраняют
  `No data` как diagnostic signal; отсутствие samples не превращается в `0s`.
- `control-plane.Identity evidence and remaining replay-safety signals` is a
  collapsed HTTP-backed forensic row. It exposes P0/P1/P2 identity anchors,
  identity gaps, replay parentage, composite identity, checkpoint anchor compare,
  and copy-friendly full values through `/ops/control-plane/identity-evidence`;
  checkpoint age vs RPO, replay duplicate detection, and richer semantic drift
  classification remain limitation notes instead of fake PromQL.
- `control-plane.Monitor: Checkpoint Freshness Lag (seconds)` is the canonical
  exact-run checkpoint freshness read path through
  `/ops/control-plane/checkpoint-freshness`. For
  `run_id=b51986c6-870b-4457-aa70-baedac2710ad`, the local manifest
  `3c803630-4652-40d0-8f8d-f26b2fb1bdd9`, terminal success ledger evidence,
  and immutable checkpoint history under `data/output/checkpoints/.history`
  classify panel `892` as checkpoint evidence present. Future audits should
  mark exact-run checkpoint gaps as `Expected Empty` only when manifest/ledger
  evidence exists but immutable checkpoint history for that exact run is absent;
  if checkpoint history exists and panel `892` still returns `UNKNOWN`, that is
  a product defect in the freshness read path.
- `dq.id=5`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=8`: query and display use hours; WARN `>=24h`, CRIT `>=72h`. The gauge
  shows the worst stale entity in TIME RANGE scope, not the freshest timestamp.
- `overview.id=111`: yellow `>=1`, red `>=5`
- `overview.id=113`: yellow `>=1`, red `>=5`
- `overview.id=114`: yellow `>=1`, red `>=10`
- `provider.id=104`: yellow `>=5%`, red `>=20%`
- `provider.id=102`: yellow `>=0.5s`, orange `>=2s`, red `>=5s`

## Частые проблемы

1. `No data`:
   проверьте `http://localhost:8000/metrics`, затем `http://localhost:9090/targets`.
1. `No data` на p95 latency panels:
   это диагностический сигнал “нет latency samples / probes / scrape window”, а
   не `0s latency`. Сначала проверьте activity/count panels рядом, потом уже
   datasource health.
1. Пустой `$provider`:
   нет ни одной серии `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`
   или `bioetl_health_check_failures_total` в metrics endpoint.
1. Пустой `$run_type`:
   нет метрик `bioetl_records_processed_total` для выбранного `$pipeline`.
1. `CLI quarantine inspect` показывает plugin error или `No data`:
   сначала различите zero matching rows и backend failure. Затем проверьте, что
   выбран конкретный `$pipeline` (не `All`) и что backend отвечает на
   `/ops/quarantine/filter-options?pipeline=<pipeline_name>`.


### Runtime dashboard layout note (Detect → Localize → Escalate)

`bioetl-runtime` использует фиксированный triage-order по трём свернутым полосам: `Detect`, `Localize`, `Escalate`.

- **Detect**: быстрый сигнал «есть ли инцидент» (blockers/failed runs/error rate/lag) и первичный выбор направления.
- **Localize**: локализация culprit stage/phase и проверка latency/backlog breakdown.
- **Escalate**: shutdown/terminal-state диагностика и handoff в tracing/log drilldown для подтверждения причины.

На first screen оставлена ровно одна рекомендация drilldown — panel `id=9991` (`First Action`). Оператор сначала читает current status, top blockers и telemetry gap; `Inspect Active Runtime Blocker Detail` открывается из CTA только когда нужен полный rule-level breakdown внутри `Detect`.
