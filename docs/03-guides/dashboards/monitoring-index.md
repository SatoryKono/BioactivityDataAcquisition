______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-14'

______________________________________________________________________

# Monitoring Docs Index

## Incident-Time Operator Index

Use this page first when an incident family is unclear. It is intentionally short.
Use the linked dashboards and artifacts for deep setup, contracts, and extension rules.

| Question / symptom | Open first | Then use | Owner doc |
| ------------------ | ---------- | -------- | --------- |
| What is currently broken or degraded? | `bioetl-overview-v2` | `Status`, `First Action`, then `0. Control Plane`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow` | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Is a Prometheus alert actually firing or pending? | `bioetl-overview-v2` | collapsed `Alert/SLO Triage` -> `Triage Alert State` | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Runtime latency, logs, memory, or alert-condition concern? | `bioetl-runtime` | `bioetl diagnostics guide`; [Observability Checklist](../../05-operations/runbooks/observability-checklist.md) | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Provider retries, slowness, or failures? | `bioetl-provider-health-v2` | `bioetl diagnostics health --json`; provider incident runbook | [Incident Response](../../05-operations/runbooks/incident-response.md) |
| DQ/freshness/quarantine signal concern? | `bioetl-dq-v2` | `bioetl diagnostics quarantine --pipeline <pipeline>` | [DQ Failure Investigation](../../05-operations/runbooks/dq-failure-investigation.md) |
| Need exact rejected record evidence? | `bioetl-silver-reject-explorer` | `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only ...` | [Quarantine Management](../../05-operations/runbooks/quarantine-management.md) |
| Replay/recovery trust question for run family? | `bioetl-control-plane-v1` | `Track: Replay / Resume Blockers in Range`, `bioetl checkpoint inspect`, `bioetl checkpoint audit-run`, then `bioetl run-manifest show <run-id|manifest-id>` for exact manifest/ledger evidence | [Checkpoint Debugging](../../05-operations/runbooks/checkpoint-debugging.md) |
| Declarative workflow step failed or skipped? | `bioetl-workflow-overview` | `bioetl_workflow_*` metrics | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Metrics/dashboard vocabulary drift check? | inventory helper | `python -m scripts.engineering.qa report-observability-metric-inventory --json` | [Observability Metrics Contract](../../04-reference/contracts/observability.md) |

Boundary rule: Prometheus/Grafana should answer aggregate operational questions.
Record-level forensics, exact replay evidence, and per-run identifiers belong in
`manifest/ledger/CLI/explorer surfaces`, not Prometheus labels.

First-screen policy rule: every operator dashboard should expose one
`ONE BIG QUESTION`, current scope, provenance summary and `First action`.
Primary dashboards `0..5` share the Overview-derived context shell
(`workflow`, `pipeline`, `run_type`, `run_id`) and common
`Provenance` / `Status` / `ID` / `Processed Records` panels. `run_id` remains
HTTP identity context, is preserved between primary dashboards, and must not
become a Prometheus label.
`Processed Records` is the shared compact Bronze/Silver/Gold stage/outcome
accounting table from `/ops/observability/processed-records`. Exact `$run_id`
scopes resolve from RunLedger artifact/metrics evidence; aggregate scopes are
backed by `bioetl_processed_records_*` recording rules with `value` and
formatted `percintage` columns, including zero-valued outcome rows and not
acting as a `$__range` throughput summary.

For `0. Control Plane`, exact identity graph evidence is available in the
collapsed `Identity evidence and remaining replay-safety signals` row. Those
tables call `/ops/control-plane/identity-evidence` for P0/P1/P2 anchors,
identity gaps, checkpoint anchor comparison, and copy-friendly full values;
they are HTTP-backed forensic surfaces, not Prometheus label filters.

Current canonical Overview baseline:

- `bioetl-overview-v2` materializes the explicit header contract
- it remains aggregate-first and routes exact run forensics to Control Plane /
  Silver Reject Explorer; its primary `run_id` selector feeds HTTP identity
  panels and is not mapped to Silver `quarantine_run_id` by generic links

## If X symptom → open dashboard Y → panel Z

| Symptom (X) | Dashboard (Y) | Panel (Z) |
| --- | --- | --- |
| "What is broken or degraded now?" | `bioetl-overview-v2` | `Status`, then `First Action` |
| Runtime failures / lag / blocker drift | `bioetl-runtime` | `Runtime Status`, `Runtime Telemetry Gap`, `Monitor Runtime Blockers`, `Runtime Blockers` |
| Provider degradation, retry exhaustion, or provider telemetry gap | `bioetl-provider-health-v2` | `Monitor GLOBAL Provider Severity Matrix`, `Inspect Provider Top Causes`, `Monitor Provider Telemetry Freshness` |
| DQ quality or quarantine increase | `bioetl-dq-v2` | `Monitor DQ Current Status`, `Monitor DQ Threshold State`, `Inspect DQ Current Reasons` |
| Replay confidence / checkpoint issues | `bioetl-control-plane-v1` | `Track: Replay / Resume Blockers in Range` |
| Exact rejected record evidence | `bioetl-silver-reject-explorer` | `Main records table` (by `payload_hash`) |

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
