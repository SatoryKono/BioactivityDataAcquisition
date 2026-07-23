______________________________________________________________________

Version: 1.1.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-12'

______________________________________________________________________

# Observability Checklist

## Trigger

- Run this checklist to verify logs, metrics, alerts, and dashboards for the local BioETL runtime.
- Escalate according to the priority declared in metadata when operator ownership is unclear.
- Use this page for operator-side validation and incident triage readiness, not for adapter implementation design.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Validation Scope

This checklist validates that operators can:

- scrape or inspect current metrics
- navigate the shipped dashboards and alert-backed signal panels
- correlate logs to the active run
- route from alerts to run-manifest diagnostics and the correct runbook
- confirm production runtime bootstrap did not fall back to NoOp logger,
  metrics, tracing, or audit without an explicit override
- confirm the required control-plane persistence profile is satisfied before the
  runtime is treated as production-ready

For observability design rules, metric naming policy, and adapter implementation
requirements, use:

- [Observability Specification](../../04-reference/contracts/observability.md)
- [Observability Layers](../../02-architecture/observability-layers.md)
- [Monitoring Guide](../01-monitoring-guide.md)
- [SLI/SLO Baseline](../sli-slo-baseline.md)
- [RULES.md](../../00-project/RULES.md)
- [ADR-017](../../02-architecture/decisions/ADR-017-observability-architecture.md)

Compatibility note for operators:

- canonical diagnostics/bootstrap discovery is
  `bioetl.composition.observability_api`
- runtime logs emit canonical `timestamp`; downstream tooling may still accept
  `ts`, but `ts` is not the canonical emitted field name
- runtime bootstrap emits `observability_initialized` with
  `logger_type`, `metrics_type`, `tracer_type`, `audit_type`,
  `required_persistence_profile`, and `preflight_status=passed` when production
  observability preflight succeeds

Unified diagnostics discovery now starts here:

```bash
bioetl diagnostics guide
```

Use that command first when the symptom family is unclear, then branch into the
specific operator-facing subcommand:

- `bioetl diagnostics health`
- `bioetl diagnostics run --run-id <run-id>`
- `bioetl diagnostics checkpoint --pipeline <pipeline>`
- `bioetl diagnostics manifest <run-id|manifest-id>`
- `bioetl diagnostics quarantine --pipeline <pipeline>`
- `python -m scripts.engineering.qa report-observability-metric-inventory --json`

### 1. Metrics Endpoint / Scrape Surface

- Confirm the local metrics endpoint responds and exports `bioetl_` metrics.
- Confirm the active run publishes the expected pipeline/runtime series.
- For non-ChEMBL publication drift symptoms, confirm the scrape surface includes
  `bioetl_publication_raw_vocab_unknown_total`.
- If `bioetl_publication_raw_vocab_unknown_total` is non-zero, triage only by
  bounded labels (`pipeline`, `provider`, `field`, `handling`) and then compare
  the affected provider/field against `configs/vocab/publication_controlled.yaml`.
- For postrun incidents, confirm the scrape surface includes:
  - `bioetl_postrun_phase_events_total`
  - `bioetl_postrun_phase_duration_seconds`
- For checkpoint/resume incidents, confirm the scrape surface includes:
  - `bioetl_checkpoint_load_events_total`
  - `bioetl_checkpoint_operator_operations_total`
  - `bioetl_checkpoint_operator_duration_seconds`
  - `bioetl_checkpoint_save_events_total`
  - `bioetl_checkpoint_save_duration_seconds`

```bash
curl http://localhost:8000/metrics | grep bioetl_
```

### 2. Log Correlation Contract

- Confirm structured logs preserve the minimum correlation fields:
  - `run_id`
  - `pipeline`
  - `pipeline_name`
  - `manifest_id` where a manifest has already been created
- Confirm the current incident or validation session can be traced from logs back
  to the active run.

```bash
cat reports/logs/bioetl.log | jq 'select(.run_id and .pipeline and .pipeline_name)'
```

### 3. Dashboard / Alert Surface

Service ownership for this section is `@bioetl-observability`.

- HTTP identity panels (datasource **BioETL Ops HTTP**): verify main health
  server `up{job="bioetl"}` and `GET http://127.0.0.1:8000/health/live` (Docker
  scrape target `bioetl:8000`). Until healthy, classify HTTP-backed identity and
  processed-record panels as backend unavailable rather than valid-empty.
  Quarantine Explorer scrape/alert was removed 2026-07-23.
- `BioETLGrafanaRendererUnavailable`: verify
  `up{job="grafana-image-renderer"}`, Grafana `rendererAvailable`, and one
  server-side render probe. Until it clears, mark screenshot evidence as render
  blocked; do not reinterpret interactive Grafana/Prometheus as unavailable.
- Panels 1–5 on `6. Alerts & SLO` expose this owner/runbook route directly and
  display Prometheus `ALERTS` output without duplicating rule thresholds.

- Check that the shipped Grafana dashboards load and that the expected filters are
  available for the active pipeline or provider.
- Run the canonical inventory helper before escalating a missing dashboard panel
  as a runtime outage:

```bash
python -m scripts.engineering.qa report-observability-metric-inventory --json
```

- Confirm the inventory output still classifies expected families as
  `direct_live_metrics` or `helper_backed_live_metrics`, not
  `registry_only_metrics` / `dead_metrics`.
- For publication vocabulary drift, confirm
  `bioetl_publication_raw_vocab_unknown_total` remains in the live metric
  inventory and that the provider/field labels map to a reviewed registry entry
  in `configs/vocab/publication_controlled.yaml`.
- Compare the inventory output with
  `grafana/prometheus-rules/bioetl_observability.yml` and the shipped dashboard
  JSON to verify that dashboard vocabulary still matches runtime and rule
  vocabulary.
- Confirm the alert-condition panels in `2. Runtime` reflect the same symptom
  family the operator is investigating.
- For checkpoint or graceful-shutdown symptoms, confirm the checkpoint save
  counter/histogram series reflect the investigated operation and status before
  moving to trace-level debugging.
- Spotlight the new `bioetl-control-plane-v1` aggregated view and confirm
  `BioETLControlPlaneReadFailureRate` is either firing or cleared, depending on
  whether control-plane reads have exceeded the 5% failure ratio limit in the
  last 30 minutes.
- For postrun symptoms, validate bounded `phase`/`status` series for
  `dq_evaluation`, `dq_reports`, `compaction`, `vacuum`, and `final_metadata`
  before switching to trace-first debugging.
- If dashboard data is missing, stop and verify metrics publication before
  troubleshooting alerts.
- If tracing is enabled and checkpoint incidents are under investigation, verify
  Tempo contains `checkpoint_save` spans for the same pipeline and time window.

### 4. Alert-to-Diagnostics Route

```bash
bioetl diagnostics guide
bioetl diagnostics manifest <run-id|manifest-id> --format json
bioetl diagnostics dossier --run-id <run-id> --format json
bioetl diagnostics dossier --manifest-id <manifest-id> --format json
```

- Confirm the returned diagnostics payload is sufficient for incident routing:

- `diagnostics.latest_status`

- `diagnostics.latest_event_type`

- `diagnostics.event_family_counts`

- `diagnostics.alert_signals`

- `diagnostics.next_steps`

- If `diagnostics.alert_signals.artifact_linkage_gap=true`, escalation must include artifact/linkage remediation before retry.
- If `diagnostics.artifact_publication_closure` is not `closed`, treat the run
  as not replay-ready; `disabled`, `partial`, and `failed` mean produced
  artifact publication evidence is not complete.
- For critical pipelines requiring `forensic_grade` evidence, confirm the
  dossier reports `status.operational_success=true`. A terminal runtime
  `success` is not sufficient when `status.operational_success_criteria`
  reports missing or degraded dossier evidence.

### 5. Drilldown and Recovery Readiness

- Confirm the operator can move from the current alert or dashboard panel into
  the matching detailed runbook:
  - runtime / fatal pipeline failure -> `pipeline-failure-critical.md`
  - DQ threshold or quarantine symptoms -> `pipeline-failure-dq.md`
  - checkpoint / resume / ledger symptoms -> `run-manifest-inspection.md` or `checkpoint-debugging.md`
- Confirm the current time window, run identifiers, and evidence snippets are
  recorded before retry or resume is attempted.

### 6. Smoke Validation Commands

Use these checks after observability changes or when dashboards seem stale:

```bash
uv run python -m pytest -q tests/integration/test_prometheus_rules_config.py
uv run python -m scripts.docs check-links --links --specs --configs
```

### 6a. Lifecycle Regression Expectations

When observability changes touch pipeline milestones or control-plane flows, tests
must assert emitted signals semantically rather than only verifying wiring or
adapter parity.

- Prefer bounded label assertions for milestone metrics such as checkpoint
  operator `operation/status`, lifecycle `dry_run`, and canonical pipeline
  `phase/status`.
- Cover at least one representative integration surface with the real
  `PipelineObserver` so canonical lifecycle events and phase histograms are
  exercised through `PipelineRunner`, not only through unit seams.
- Keep assertions low-cardinality: use canonical event names and bounded labels,
  not free-form message text.

Targeted regression commands for lifecycle/control-plane observability changes:

```bash
uv run pytest -q tests/unit/application/services/test_checkpoint_service.py
uv run pytest -q tests/unit/application/services/test_checkpoint_compatibility_service.py
uv run pytest -q tests/unit/infrastructure/control_plane/test_file_artifact_lifecycle_store.py
uv run pytest -q tests/integration/test_runner_lifecycle.py
```

### 6b. 15-pipeline closure campaign

Use the QA entry point to inventory the exact ChEMBL config/registry universe
before an execution run:

```bash
python -m scripts.engineering.qa run-observability-closure-campaign \
  --audit-root /absolute/fresh/audit-root \
  --tracing-mode both
```

Execution is fail-closed. It requires existing canonical data and log roots,
a fresh audit root, both explicit tracing modes, and one typed JSON evidence
artifact for every external acceptance category:

```bash
python -m scripts.engineering.qa run-observability-closure-campaign \
  --audit-root /absolute/fresh/audit-root \
  --canonical-data-root /absolute/canonical/data \
  --canonical-log-root /absolute/canonical/logs \
  --tracing-mode both \
  --execute \
  --evidence tracing_parity=/absolute/fresh/audit-root/evidence/tracing_parity.json \
  --evidence metric_reconciliation=/absolute/fresh/audit-root/evidence/metric_reconciliation.json \
  --evidence workflow_correlation=/absolute/fresh/audit-root/evidence/workflow_correlation.json \
  --evidence metric_surface=/absolute/fresh/audit-root/evidence/metric_surface.json \
  --evidence dashboard_variables=/absolute/fresh/audit-root/evidence/dashboard_variables.json \
  --evidence zero_evidence=/absolute/fresh/audit-root/evidence/zero_evidence.json \
  --evidence scrape_targets=/absolute/fresh/audit-root/evidence/scrape_targets.json \
  --evidence render_stability=/absolute/fresh/audit-root/evidence/render_stability.json \
  --evidence promtool=/absolute/fresh/audit-root/evidence/promtool.json \
  --evidence online_run=/absolute/fresh/audit-root/evidence/online_run.json
```

Each evidence file is unique, resides below `AUDIT_ROOT/evidence`, and carries
`schema_version: 1`, its matching `evidence_type`, `status: pass`, the exact
campaign `source_revision`, a timezone-aware `generated_at`, and the
category-specific numeric `summary`. The runner hashes each artifact into the
final report. It returns non-zero for missing/malformed/stale evidence, a
timeout or failed/ambiguous pipeline attempt, tracing-mode gaps, registry/config
drift, reused audit state, or any canonical-root mutation. The specialized
Prometheus, dashboard render, workflow and online-run checks remain the
producers of those typed artifacts; this command is their final aggregation
and immutable-root gate.

### 7. Operator Sign-off

- [ ] Metrics endpoint is reachable
- [ ] Logs preserve correlation fields for the active run
- [ ] Dashboard and alert-condition panels match the investigated symptom family
- [ ] `bioetl diagnostics guide` points to an unambiguous next command
- [ ] `bioetl diagnostics manifest` returns usable diagnostics
- [ ] The next runbook in the incident path is unambiguous

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
