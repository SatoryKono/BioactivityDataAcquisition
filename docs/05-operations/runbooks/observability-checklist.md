---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Priority: P2
Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
Last verified: '2026-04-02'
---

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

For observability design rules, metric naming policy, and adapter implementation
requirements, use:

- [Monitoring Guide](../01-monitoring-guide.md)
- [RULES.md](../../00-project/RULES.md)
- [ADR-017](../../02-architecture/decisions/ADR-017-observability-architecture.md)

### 1. Metrics Endpoint / Scrape Surface

- Confirm the local metrics endpoint responds and exports `bioetl_` metrics.
- Confirm the active run publishes the expected pipeline/runtime series.

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
cat logs/bioetl.log | jq 'select(.run_id and .pipeline and .pipeline_name)'
```

### 3. Dashboard / Alert Surface

- Check that the shipped Grafana dashboards load and that the expected filters are
  available for the active pipeline or provider.
- Confirm the alert-condition panels in `2. Runtime` reflect the same symptom
  family the operator is investigating.
- If dashboard data is missing, stop and verify metrics publication before
  troubleshooting alerts.

### 4. Alert-to-Diagnostics Route

```bash
bioetl run-manifest show <run-id|manifest-id> --format json
```

- Confirm the returned diagnostics payload is sufficient for incident routing:

- `diagnostics.latest_status`
- `diagnostics.latest_event_type`
- `diagnostics.event_family_counts`
- `diagnostics.alert_signals`
- `diagnostics.next_steps`

- If `diagnostics.alert_signals.artifact_linkage_gap=true`, escalation must include artifact/linkage remediation before retry.

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

### 7. Operator Sign-off

- [ ] Metrics endpoint is reachable
- [ ] Logs preserve correlation fields for the active run
- [ ] Dashboard and alert-condition panels match the investigated symptom family
- [ ] `run-manifest show` returns usable diagnostics
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
