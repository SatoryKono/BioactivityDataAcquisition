______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-13'

______________________________________________________________________

# Monitoring Docs Index

> The seven JSON dashboards remain the production fallback and rollback SSOT.
> Optional `bioetl-scenes-app` routes are read-only, shadow-only, and disabled
> by default. See [Optional Scenes dual path](scenes-dual-path.md).

## Incident-Time Operator Index

Use this page first when an incident family is unclear. It is intentionally short.
Use the linked dashboards and artifacts for deep setup, contracts, and extension rules.

For the authoritative shipped dashboard mapping
(`JSON -> docs -> datasources -> versioning policy`), use
[dashboard-inventory.md](dashboard-inventory.md).

| Question / symptom | Open first | Then use | Owner doc |
| ------------------ | ---------- | -------- | --------- |
| What is currently broken or degraded? | `bioetl-overview-v2` (Fleet) | `Status`, `Inputs` matrix, compact `First Action`, then `0. Trust`, `2. Pipeline Diagnostics`, `3. Provider Health`, `4. Data Quality`, Incident Workspace, Run Explorer | [Operator UX v2](operator-ux-v2.md) / [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Unified incident suspects / alert entry | `bioetl-incident-v1` | Ranked Suspects → domain explorers | [migration-map-v2](migration-map-v2.md) |
| Single-run identity / processed records | `bioetl-run-explorer-v1` | ID + Processed Records (HTTP); Trust for resume | [Run Explorer panels](panels/bioetl-run-explorer-v1-panels.md) |
| Is a Prometheus alert actually firing or pending? | `bioetl-overview-v2` | first-screen `Alert/SLO Triage` -> `Triage Alert State`, then `Alert/SLO Triage (Overview collapsed row)` | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Need a dashboard dedicated to active alert state or SLO pressure? | `bioetl-overview-v2 (Alert/SLO Triage)` | `Active Alert Status`, `Firing Alerts / Range`, `Firing Alert Details` | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Runtime latency, logs, memory, or alert-condition concern? | `bioetl-runtime` | `bioetl diagnostics guide`; [Observability Checklist](../../05-operations/runbooks/observability-checklist.md) | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Provider retries, slowness, or failures? | `bioetl-provider-health-v2` | `bioetl diagnostics health --json`; provider incident runbook | [Incident Response](../../05-operations/runbooks/incident-response.md) |
| DQ/freshness/quarantine signal concern? | `bioetl-dq-v2` | `bioetl diagnostics quarantine --pipeline <pipeline>` | [Pipeline Failure DQ](../../05-operations/runbooks/pipeline-failure-dq.md) |
| Need exact Silver structural rejected record evidence? | CLI (Explorer UI removed) | `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only ...` (`FILTERED_OUT_SILVER` legacy alias only); DQ aggregates stay in `bioetl-dq-v2` | [Quarantine Management](../../05-operations/runbooks/quarantine-management.md) |
| Need Gold contract/semantic reject evidence? | `bioetl-dq-v2` Gold reject panels / processed-records surfaces | Start from `Inspect Gold Reject Outcomes by Pipeline`; do not use `--silver-filter-only` | [Quarantine Management](../../05-operations/runbooks/quarantine-management.md) |
| Replay/recovery trust question for run family? | `bioetl-control-plane-v1` | `Track Replay Blockers in Range`, `bioetl checkpoint inspect`, `bioetl checkpoint audit-run`, then `bioetl run-manifest show <run-id|manifest-id>` for exact manifest/ledger evidence | [Checkpoint Debugging](../../05-operations/runbooks/checkpoint-debugging.md) |
| Declarative workflow step failed or skipped? | `bioetl-runtime (workflow band)` | `bioetl_workflow_*` metrics | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Metrics/dashboard vocabulary drift check? | inventory helper | `python -m scripts.engineering.qa report-observability-metric-inventory --json` | [Observability Metrics Contract](../../04-reference/contracts/observability.md) |

Boundary rule: Prometheus/Grafana should answer aggregate operational questions.
Record-level forensics, exact replay evidence, and per-run identifiers belong in
`manifest/ledger/CLI/explorer surfaces`, not Prometheus labels.

First-screen policy rule: every operator dashboard should expose one
`ONE BIG QUESTION`, current scope, provenance summary and `First action`.
Primary dashboards `0..5` share the Overview-derived context shell
(`workflow`, `pipeline`, `run_type`, `run_id`) and common
`Inspect Scope & Evidence` / `Status` / `ID` / `Processed Records` panels. `run_id` remains
HTTP identity context, is preserved between primary dashboards, and must not
become a Prometheus label.
The shipped question/scope/evidence readability contract uses the `4. Data Quality` visual
pattern across all seven dashboards: 16px body, 18px question, orange accent,
normal wrapping, and a four-grid-row first-screen panel. Run Explorer maps its
stable `id=1` panel to `Inspect Run Selection & Evidence`.
`Processed Records` is the shared compact Bronze/Silver/Gold stage/outcome
accounting table from `/ops/observability/processed-records`. Exact `$run_id`
scopes resolve from RunLedger artifact/metrics evidence; aggregate scopes are
backed by `bioetl_processed_records_*` recording rules with `value` and
formatted canonical `percentage` fields, including zero-valued outcome rows.
Every `Inspect`/`Review Processed Records` table displays `parameter`, `value`,
and canonical `percentage`; both numeric columns are right-aligned. Internal `row_status` is hidden,
the payload uses canonical `percentage` only, and the table does not act as a
`$__range` throughput summary.
All **seven** shipped dashboards share one theme-safe navigation panel: numbered
bus `0..6`. Loki/Tempo Explore adjuncts and Silver Reject Explorer were removed
2026-07-23. The bus wraps at `1024px` and stays readable in dark and light themes.

The shared `ID` and `Processed Records` cards are HTTP-backed via
**BioETL Ops HTTP** (main `bioetl health server` `:8000`). Their empty state must
be interpreted only after `/health/live` (and control-plane readiness) respond;
backend-down, invalid scope, and true zero/absent run are distinct operator states.

For `0. Trust`, exact identity graph evidence is available by expanding
the collapsed-by-default `Inspect Run Identity Evidence` row. Those
tables call `/ops/control-plane/identity-evidence` for P0/P1/P2 anchors,
identity gaps, checkpoint anchor comparison, and copy-friendly full values;
they are HTTP-backed forensic surfaces, not Prometheus label filters.

Current canonical Overview baseline:

- `bioetl-overview-v2` materializes the explicit header contract
- it remains aggregate-first and routes exact run forensics to Control Plane and
  CLI quarantine inspect; its primary `run_id` selector feeds HTTP identity
  panels only (not Prometheus labels)

## If X symptom → open dashboard Y → panel Z

| Symptom (X) | Dashboard (Y) | Panel (Z) |
| --- | --- | --- |
| "What is broken or degraded now?" | `bioetl-overview-v2` | `Status`, then `First Action` |
| Runtime failures / lag / blocker drift | `bioetl-runtime` | trust-gated `Runtime Status`, `Metrics Evidence`, `Monitor Runtime Blockers`, `Runtime Blockers`; `INCOMPLETE` means repair scrape/rules first |
| Provider degradation, retry exhaustion, or provider telemetry gap | `bioetl-provider-health-v2` | `Monitor GLOBAL Provider Severity Matrix`, `Inspect Provider Top Causes`, `Monitor Provider Telemetry Freshness` |
| DQ quality or quarantine increase | `bioetl-dq-v2` | `Monitor DQ Current Status`, `Now · DQ Threshold State`, `Now · DQ Current Reasons`, then TIME RANGE freshness in hours (SLA 24h/72h) |
| Replay confidence / checkpoint issues | `bioetl-control-plane-v1` | evidence-aware `Status`; `INCOMPLETE` blocks replay/resume approval, then inspect the four trust cards |
| Exact rejected record evidence | CLI `bioetl quarantine inspect` | use `--pipeline` / filters; Grafana holds aggregate DQ only (`bioetl-dq-v2`) |

## Architecture Map

| Layer / surface | Responsibility | Source of truth |
| --------------- | -------------- | --------------- |
| Domain port | transport-neutral observability contracts | `src/bioetl/domain/ports/observability/` |
| Application emitters | metric and trace callsites | `src/bioetl/application/**` |
| Infrastructure adapter | Prometheus registry / exposition | `src/bioetl/infrastructure/observability/` |
| Composition | observability wiring and diagnostics assembly | `src/bioetl/composition/observability_api.py` |
| Grafana dashboards | operator panels, links, variables, Explore handoffs | `grafana/dashboards/*.json` |
| Prometheus rules | alert and recording rules | `grafana/prometheus-rules/bioetl_observability.yml` |
| Contracts/docs | metric contracts and operator docs | `docs/04-reference/contracts/observability.md` |

## Operator scenarios (S1–S6)

See [operator-scenarios-s1-s6.md](operator-scenarios-s1-s6.md) for the post-simplification playbook (epic #6570 / #6577).
