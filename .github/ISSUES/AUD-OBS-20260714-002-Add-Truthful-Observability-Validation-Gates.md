---
title: "[AUD-OBS-20260714][P1] Add truthful CI and scheduled gates for observability validators"
labels: observability, grafana, runtime, validation, critical, prometheus
assignees: []
---

## Audit provenance

- Audit date: `2026-07-14`.
- Follow-up to closed issues #6283, #6284, #6285, and #6286.
- Evidence anchor:
  `docs/00-project/ai/audit/observability-issues/VALIDATION-SUMMARY.md`.
- Validators produced by the closed work:
  - `scripts/ops/observability/validate_live_observability.py`
  - `scripts/ops/observability/validate_metric_to_panel_mapping.py`
  - `scripts/ops/observability/validate_emitter_contracts.py`
  - `scripts/ops/observability/grafana/audit_live_grafana_panels.py`

## Problem

The audit validators have one-time local evidence but are not invoked by the
tracked GitHub Actions workflows. The validation summary explicitly identifies
CI/CD integration and scheduled audits as the next phase.

Running every validator indiscriminately in every PR would also be misleading:
some checks are repository-static, some require Prometheus/Grafana, and the full
application-level lane requires representative BioETL and HTTP-backend data.
The current results already demonstrate why verdict policy matters: `199`
variable-dependent checks were skipped and an infrastructure run with the
application absent was correctly partial. CI must not convert either condition
into an unqualified green end-to-end verdict.

## Required outcome

Add change-aware, truthful automation with separate execution contracts:

1. a hermetic PR lane for repository-static observability contracts;
2. a monitoring-stack lane for live Grafana/Prometheus validation;
3. a scheduled or manually dispatched application-level lane once the
   representative validation contract is available;
4. explicit exit-code and verdict semantics for pass, expected-empty, partial,
   skipped, and failure states;
5. uploaded machine-readable evidence for every non-hermetic run.

## Acceptance criteria

- [ ] Tracked workflow configuration invokes the applicable observability
  validators when dashboard, Prometheus-rule, observability-emitter, datasource,
  selector/navigation-contract, or validator files change.
- [ ] The PR lane is hermetic and does not require a live external service,
  personal token, production credential, or workstation-local configuration.
- [ ] If a current validator cannot support a hermetic mode, the workflow uses
  its repository-backed tests or the validator gains an explicit static mode;
  missing live services are not represented as successful live validation.
- [ ] A manual/scheduled live lane validates the existing local monitoring stack
  and publishes JSON reports, logs, and rendered/audit evidence as workflow
  artifacts with a documented retention period.
- [ ] The application-level lane is enabled only with the tracked representative
  matrix and tolerances from `AUD-OBS-20260714-001`; until then, automation
  reports the scope as infrastructure-only.
- [ ] Exit codes and summaries fail on query, datasource, incorrect-value,
  stale-data, filter, render, forbidden-emitter, or contract violations.
- [ ] `EMPTY_EXPECTED`, a justified optional datasource, and a deliberately
  unsupported check are reported separately; skipped or partial checks never
  inflate the pass rate or produce an end-to-end-complete claim.
- [ ] Workflow concurrency, timeouts, cleanup, and service readiness checks keep
  the live lane deterministic and prevent orphaned monitoring processes.
- [ ] Unit/repository-backed tests cover validator exit codes, report schema,
  expected-empty semantics, unavailable-service semantics, and workflow command
  routing.
- [ ] Contributor/operator documentation explains which lane runs on PR,
  schedule, and manual dispatch and how to reproduce each lane locally.
- [ ] Automation uses read-only Prometheus/Grafana API operations and does not
  enable or call Prometheus admin endpoints, reload endpoints, destructive
  Pushgateway operations, or write-side Grafana actions.
- [ ] No `.env` or `.env.*` file is created or modified, and no secret is written
  to workflow logs or uploaded artifacts.
- [ ] No forensic identifier or unbounded value is introduced as a Prometheus
  label to make CI fixtures easier.
- [ ] No technical-debt budget, exemption, hotspot threshold, or family cap is
  increased.

## Validation

- Exercise the PR lane on an observability-relevant change and on an unrelated
  change to prove path routing.
- Exercise the live lane in healthy, expected-optional, service-unavailable, and
  invalid-query scenarios and verify workflow conclusions plus uploaded report
  schemas.
- Run the repository-backed tests for all four validator/tooling entry points.
- Validate modified workflow YAML and run the repository's relevant workflow,
  architecture, docs-drift, and generated-artifact routing guards.

## Dependencies and overlap

- `AUD-OBS-20260714-001` owns the representative application matrix and numeric
  reconciliation contract; this issue owns automation and verdict truthfulness.
- #6266 owns typed governance inventory and panel/docs bidirectional parity.
- #6267 owns Prometheus rule semantic coverage and toolchain version parity.
- #4870 already closed degraded runtime-cardinality release-gate behavior; do
  not recreate or weaken that gate.
- #5929 already closed in-memory observability-emission integration coverage;
  this issue does not duplicate those application tests.

## Guardrails

- Preserve Local-Only operation and keep monitoring services optional outside
  their explicit validation lane.
- Do not create or modify `.env` or `.env.*`.
- Do not expand metric label cardinality or move forensic data into Prometheus.
- Do not increase technical-debt budgets or weaken existing gates.
