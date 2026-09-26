---
title: "[AUD-OBS-20260714][P1] Complete application-level observability validation and value reconciliation"
labels: observability, grafana, runtime, validation, critical, prometheus
assignees: []
---

## Audit provenance

- Audit date: `2026-07-14`.
- Follow-up to closed issues #6283, #6284, and #6286.
- Durable evidence:
  - `docs/00-project/ai/audit/observability-issues/VALIDATION-SUMMARY.md`
  - `docs/00-project/ai/audit/observability-issues/OBS-002-validation-findings.md`
  - `docs/00-project/ai/audit/observability-issues/OBS-003-validation-findings.md`
  - `docs/00-project/ai/audit/observability-issues/OBS-006-validation-findings.md`
- Local generated evidence:
  - `reports/observability/live-validation/validation-report-20260714-083129.json`
  - `reports/observability/metric-panel-validation/metric-panel-report-20260714-090951.json`
  - `reports/observability/datasource-compliance/datasource-audit-report.json`

The generated reports are ignored local evidence. The confirmed residual gap and
completion contract are embedded below so the issue remains independently
actionable.

## Problem

The closed validation issues prove that the monitoring infrastructure loads and
that executable dashboard queries are valid, but they do not yet prove the full
runtime chain:

`representative BioETL action -> emitted sample -> Prometheus/rule value -> dashboard value -> operator drilldown`.

The existing evidence explicitly records these limitations:

- live infrastructure validation passed `6/7` checks while the BioETL
  application was not running;
- metric-to-panel validation executed `611/611` eligible PromQL checks but
  skipped `199` template-variable checks;
- datasource compliance was proven at configuration/boundary level while full
  HTTP-panel behavior still requires the BioETL and Quarantine Explorer
  backends;
- application-level performance, representative-data behavior, and numerical
  reconciliation remain partial;
- the production URL/auth model, retention policy, representative dataset size,
  and numerical tolerances were not established by the audit and must not be
  guessed.

Without a representative application run, a dashboard can remain syntactically
valid while presenting stale, empty, incorrectly reduced, or numerically wrong
values.

## Required outcome

Create a reproducible, local-only application-level validation lane that:

1. defines a bounded representative run matrix and explicit reconciliation
   tolerances;
2. exercises normal pipeline/workflow telemetry plus a controlled DQ or
   quarantine path using current repository-supported fixtures/configuration;
3. validates Prometheus samples, recording/alert rules, Grafana panels,
   selectors, navigation, and HTTP-backed detail panels against the same time
   window;
4. distinguishes expected emptiness from query, datasource, filter, rendering,
   stale-data, and incorrect-value failures;
5. publishes durable evidence without moving forensic identities into
   Prometheus labels.

## Acceptance criteria

- [ ] A tracked validation manifest identifies the representative pipelines or
  workflows, fixture/dataset, required local services, time window, scrape and
  evaluation lag, and numerical tolerances. It contains no credentials,
  workstation paths, or environment-specific production assumptions.
- [ ] The lane uses the existing local monitoring/runtime surfaces; it does not
  introduce a mandatory external orchestrator or production dependency.
- [ ] At least one successful representative run and one controlled DQ,
  quarantine, replay, or blocker scenario produce expected telemetry and
  operator drilldowns.
- [ ] Active targets, rules, metadata, bounded selector values, all eight
  shipped dashboards, and relevant Prometheus/HTTP/Loki/Tempo handoffs receive
  explicit verdicts.
- [ ] The `199` previously skipped variable-dependent checks are either executed
  with resolved bounded variables or individually classified with a documented
  non-executable reason; a skipped check is not counted as a pass.
- [ ] HTTP-backed identity/detail panels are validated with the required local
  backend running, including valid-empty, backend-down, and exact-context
  behavior.
- [ ] A timestamp-aligned value-reconciliation matrix records, for each selected
  critical panel, the runtime artifact/value, raw metric, recording-rule value,
  rendered dashboard value, tolerance, and verdict.
- [ ] The evidence covers current status/trust gaps, processed-record accounting,
  provider errors or latency, DQ/reject accounting, and replay/blocker semantics
  where those signals are present in the representative matrix.
- [ ] Every panel uses one of the audit verdicts `PASS`, `EMPTY_EXPECTED`,
  `EMPTY_UNEXPECTED`, `QUERY_ERROR`, `DATASOURCE_ERROR`, `INCORRECT_VALUE`,
  `STALE_DATA`, `FILTER_ERROR`, or `RENDER_ERROR`.
- [ ] Evidence is captured through read-only Grafana/Prometheus/runtime APIs.
  Prometheus admin endpoints, reload endpoints, destructive Pushgateway calls,
  and write-side dashboard actions are not used.
- [ ] Optional tracing-profile absence is reported as an availability-policy
  result rather than silently converted to either pass or failure.
- [ ] No `run_id`, `manifest_id`, `record_id`, `payload_hash`, filesystem path,
  URL, raw exception, or other unbounded forensic value is added to Prometheus
  labels.
- [ ] A durable summary is added under
  `docs/00-project/ai/audit/observability-issues/`, with generated raw evidence
  stored under `reports/observability/` according to repository routing policy.
- [ ] Relevant validator and contract tests pass, and no technical-debt budget,
  exemption, hotspot threshold, or family cap is increased.

## Validation

- Run the application-level lane twice against the same deterministic fixture
  and compare the resulting verdict/value matrices.
- Run `python scripts/ops/observability/validate_live_observability.py` against
  the active local application stack.
- Run `python scripts/ops/observability/validate_metric_to_panel_mapping.py`
  with resolved selector inputs.
- Run `python -m scripts.ops audit-live-grafana` with the required local
  datasources available.
- Re-run the affected repository-backed and architecture tests discovered from
  the touched validator, dashboard, contract, and documentation surfaces.

## Dependencies and overlap

- #6283, #6284, and #6286 are closed infrastructure/configuration proofs and
  must not be reopened for this residual application-level scope.
- #6266 owns typed metric/panel/documentation inventory and bidirectional drift
  checks.
- #6267 owns Prometheus rule semantic coverage and Prometheus/Pushgateway version
  parity.
- Existing runtime-cardinality governance owns its current thresholds and review
  artifacts; this issue consumes that evidence but does not redefine it.

## Guardrails

- Preserve Local-Only operation.
- Do not create or modify `.env` or `.env.*`.
- Keep exact identity and record-level forensics in control-plane, quarantine,
  logs, traces, manifests, ledgers, and CLI surfaces.
- Do not increase technical-debt budgets or weaken existing gates.
