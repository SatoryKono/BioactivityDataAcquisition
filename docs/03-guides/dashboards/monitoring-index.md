______________________________________________________________________

Version: 1.0.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Monitoring Docs Index

## Incident-Time Operator Index

Use this page first when an incident family is unclear. It is intentionally short.
Use the linked dashboards and artifacts for deep setup, contracts, and extension rules.

| Question / symptom | Open first | Then use | Owner doc |
| ------------------ | ---------- | -------- | --------- |
| What is currently broken or degraded? | `bioetl-overview-v2` | `System Status`, `Next Action`, then `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `6. Workflow Overview`, `Control Plane / Replay Safety` | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Runtime latency, logs, memory, or alert-condition concern? | `bioetl-runtime` | `bioetl diagnostics guide`; [Observability Checklist](../../05-operations/runbooks/observability-checklist.md) | [Monitoring Guide](../../05-operations/01-monitoring-guide.md) |
| Provider retries, slowness, or failures? | `bioetl-provider-health-v2` | `bioetl diagnostics health --json`; provider incident runbook | [Incident Response](../../05-operations/runbooks/incident-response.md) |
| DQ/freshness/quarantine signal concern? | `bioetl-dq-v2` | `bioetl diagnostics quarantine --pipeline <pipeline>` | [DQ Failure Investigation](../../05-operations/runbooks/dq-failure-investigation.md) |
| Need exact rejected record evidence? | `bioetl-silver-reject-explorer` | `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only ...` | [Quarantine Management](../../05-operations/runbooks/quarantine-management.md) |
| Replay/recovery trust question for run family? | `bioetl-control-plane-v1` | `Replay / Resume Blockers`, `bioetl checkpoint inspect`, `bioetl checkpoint audit-run` | [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md) |
| Declarative workflow step failed or skipped? | `bioetl-workflow-overview` | `bioetl_workflow_*` metrics | [Dashboard v2 Usage](dashboard-v2-usage.md) |
| Metrics/dashboard vocabulary drift check? | inventory helper | `python -m scripts.engineering.qa report-observability-metric-inventory --json` | [Observability Metrics Contract](../../04-reference/contracts/observability.md) |

Boundary rule: Prometheus/Grafana should answer aggregate operational questions.
Record-level forensics, exact replay evidence, and per-run identifiers belong in
`manifest/ledger/CLI/explorer surfaces`, not Prometheus labels.

## If X symptom → open dashboard Y → panel Z

| Symptom (X) | Dashboard (Y) | Panel (Z) |
| --- | --- | --- |
| "What is broken or degraded now?" | `bioetl-overview-v2` | `System Status`, then `Next Action` |
| Runtime failures / lag / blocker drift | `bioetl-runtime` | `Runtime Blockers / 15m`, `Worst Stage Lag / 15m` |
| Provider degradation or retry exhaustion | `bioetl-provider-health-v2` | `Current Provider Health Status`, `Retries Exhausted by Provider / Operation` |
| DQ quality or quarantine increase | `bioetl-dq-v2` | `Data Quality Score (Volume-weighted)`, `Records Quarantined` |
| Replay confidence / checkpoint issues | `bioetl-control-plane-v1` | `Replay / Resume Blockers` |
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

