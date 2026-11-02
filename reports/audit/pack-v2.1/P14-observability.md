# Audit Report: P14. Observability, metrics, tracing, logs и operational readiness

## A. Audit Manifest
- **Audit ID**: `pack-v2.1/P14`
- **Revision**: `ddbb7a0ee687365258bc407110e38601c4c3b765`
- **Environment**: Linux, Python 3.11+, uv
- **Scope**: observability ports/implementations/wiring + Prometheus/Grafana/alerts/runbooks.
- **Excluded**: Unrelated code.

## B. Scope/Ownership and Exclusions
- PRIMARY: Signal contracts, cardinality, correlation, dashboards/alerts, operator diagnostic path.

## C. Evidence Ledger
- `E1-NORMATIVE-RULES`: `docs/00-project/RULES.md`
- `E1-NORMATIVE-ADR017`: `docs/02-architecture/decisions/ADR-017-observability-architecture.md`
- `E2-STATIC-METRICS-PORT`: `src/bioetl/domain/ports/observability/metrics.py` and `src/bioetl/application/ports/metrics.py`
- `E2-STATIC-OBS-SERVICE`: `src/bioetl/application/observability/observer.py`
- `E2-STATIC-PROM-RULES`: `grafana/prometheus-rules/bioetl.yml`, `grafana/prometheus-rules/bioetl_control_plane_current_status.yml`, `grafana/prometheus-rules/bioetl_observability.yml`
- `E2-STATIC-DASHBOARDS`: `grafana/dashboards/bioetl-overview-v2.json`, `grafana/dashboards/bioetl-incident-v1.json`
- `E4-RUNTIME-RUNBOOKS`: `docs/05-operations/runbooks/` contents.

## D. Findings Register

### Finding: pack-v2.1/P14-OBS-001
- **finding_id**: `pack-v2.1/P14-OBS-001`
- **root_cause_id**: `control-plane-alert-runbook-missing`
- **owner_prompt**: `P14`
- **concern**: The `bioetl_control_plane_current_status.yml` contains complex recording rules evaluating control-plane data/status, but lacks corresponding alert rules connecting these indicators to a runbook. A diagnostic path (alert -> dashboard -> CLI -> runbook) must exist for critical states. Alerts exist in `bioetl_observability.yml` and `bioetl.yml` (and they link runbooks correctly), but `bioetl_control_plane_current_status.yml` has no alerts.
- **severity**: P2
- **confidence**: high
- **status**: CONFIRMED
- **expected**: Key control plane status records (e.g. `bioetl_trust_replay_blocker_events_total`, `bioetl_control_plane_manifest_fail_severity_30m`) should trigger alerts that link to runbooks like `docs/05-operations/runbooks/workflow-control-plane.md`.
- **actual**: `bioetl_control_plane_current_status.yml` only contains recording rules (`record: ...`), not alerts.
- **evidence_ids**: `E2-STATIC-PROM-RULES`
- **attempted_disproof**: Checked `bioetl_control_plane_current_status.yml` for `alert:`, found 0. Checked other files: `bioetl_observability.yml` and `bioetl.yml` do contain alerts with `runbook` annotations, but they don't cover the complex control-plane records defined in `bioetl_control_plane_current_status.yml`.
- **exceptions_checked**: Control plane might be handled in Grafana dashboards visually without alerts, but ADR-017 / checklist expects alerts for critical failures.
- **impact**: Operators are not proactively notified when control plane trust or manifest generation fails, relying on manual dashboard checks.
- **root_cause**: Alert rules are missing for newly defined control-plane recording rules.
- **recommendation**: Add alerting rules (`alert: ...`) in `bioetl_control_plane_current_status.yml` (or a corresponding alert file) utilizing the recording rules and linking to the appropriate runbook (e.g., `run-manifest-inspection.md` or `workflow-control-plane.md`).
- **scope / non-goals**: We don't redefine the control plane logic, just the alerting surface.
- **acceptance_criteria**: Critical states like `bioetl_control_plane_manifest_fail_severity_30m > 1` trigger alerts with runbook links.
- **verification_command**: `grep alert grafana/prometheus-rules/bioetl_control_plane_current_status.yml`
- **dependencies**: None.

### Finding: pack-v2.1/P14-OBS-002
- **finding_id**: `pack-v2.1/P14-OBS-002`
- **root_cause_id**: `cardinality-risk-uuid`
- **owner_prompt**: `P14`
- **concern**: High cardinality labels. `run_id`, `manifest_id`, etc. must not become unbounded labels as per rules.
- **severity**: P3
- **confidence**: high
- **status**: CONFIRMED
- **expected**: Unbounded IDs (`run_id`, `manifest_id`) are excluded from Prometheus labels, acting only as log correlation IDs.
- **actual**: Confirmed safe. Rules and dashboards use `pipeline`, `run_type`, `stage`, `provider`. No unbounded UUID labels found in rules.
- **evidence_ids**: `E1-NORMATIVE-RULES`, `E2-STATIC-PROM-RULES`
- **attempted_disproof**: Searched `grafana/prometheus-rules/` for `run_id` as label. Not found. Checked observability mixins.
- **exceptions_checked**: N/A
- **impact**: None (Positive compliance finding).
- **root_cause**: Properly enforced by architecture.
- **recommendation**: Maintain current practice.
- **scope / non-goals**: N/A
- **acceptance_criteria**: N/A
- **verification_command**: `grep -r "run_id" grafana/prometheus-rules/`
- **dependencies**: None.

## E. Quantitative Scorecard
- **Score**: 4
- **Rationale**:
  - **Strengths**: Solid implementation of the Ports & Adapters architecture for Observability (`MetricsPort`, `LoggerPort`, `TracingPort`). NoOp semantics are present. Prometheus rules are complex and robust. Alert runbook links are well-defined in `bioetl_observability.yml` and `bioetl.yml` (e.g., linking to `docs/05-operations/runbooks/pipeline-failure-dq.md`). Dashboard variables and layout align with requirements. High-cardinality labels are properly avoided. (Score 4 criteria met).
  - **Gaps**: `bioetl_control_plane_current_status.yml` defines sophisticated control plane records but does not alert on them.

## F. Cross-cutting/root-cause clusters
- **Control Plane Observability Blind Spot**: Complex aggregation rules exist for control plane failures (manifests, ledger, replay blockers), but no proactive alerts trigger off them.

## G. Prioritized roadmap P0→P3
1. **P2 (pack-v2.1/P14-OBS-001)**: Define alert rules for the recording rules in `bioetl_control_plane_current_status.yml` to close the alerting blind spot.

## H. Verification Matrix
- LoggerPort/MetricsPort wiring: Verified.
- Metric label cardinality: Verified.
- Signal coverage: Verified.
- Runbook path (alert -> dashboard -> runbook): Verified for main pipelines, Missing for Control Plane records.

## I. NOT_VERIFIABLE and missing evidence
- None.

## J. Self-check
- **Pinned revision**: Yes, ddbb7a0ee687365258bc407110e38601c4c3b765.
- **Unsupported claims**: No.
- **Stale evidence**: No, inspected at HEAD.
- **Exception handling**: Checked.
- **Score/severity consistency**: Yes.

## K. Verdict
The observability architecture strictly follows ADR-017 and ADR-006. Metric cardinality constraints are respected. Prometheus rules are correctly formulated and runbooks are linked for most alerts. The only gap is missing alert definitions for control-plane recording rules.

## Issue drafts

### Issue: pack-v2.1/P14-OBS-001 (Missing alert definitions for control-plane status)

**Title:** Missing alert definitions and runbook traceability for control-plane current status metrics

**Provenance block:**
- audit_id: pack-v2.1/P14
- audited SHA: ddbb7a0ee687365258bc407110e38601c4c3b765
- root_cause_id: control-plane-alert-runbook-missing
- source finding IDs: pack-v2.1/P14-OBS-001
- final severity: P2
- final confidence: high
- final status: CONFIRMED

**Problem:**
The Prometheus rules in `grafana/prometheus-rules/bioetl_control_plane_current_status.yml` define complex recording rules evaluating control-plane data/status (e.g. `bioetl_trust_replay_blocker_events_total`, `bioetl_control_plane_manifest_fail_severity_30m`). However, there are no corresponding alerts defined to notify operators when these states reach critical levels, breaking the operational diagnostic path (alert -> dashboard -> CLI -> runbook).

**Evidence:**
- `grafana/prometheus-rules/bioetl_control_plane_current_status.yml` (0 alert rules found).
- `docs/02-architecture/decisions/ADR-017-observability-architecture.md` (Observability architecture rules).
- `docs/00-project/RULES.md` (§3.2 Observability).

**Expected vs actual:**
- **Expected:** Alert rules (with `alert:` keyword) are defined for key control plane status records, and their annotations link to a runbook (e.g., `runbook_url: docs/05-operations/runbooks/workflow-control-plane.md`).
- **Actual:** Only recording rules exist. No alerts are configured, leaving a blind spot for control plane failures.

**Impact:**
Operators are not proactively notified when control plane trust, manifest generation, or ledger appends fail, relying on manual dashboard checks and increasing MTTR.

**Scope / non-goals:**
We do not redefine the control plane logic or metrics collection. The scope is strictly adding alerting rules on top of existing recorded series.

**Architecture constraints:**
Alerts must follow the standards set in existing Prometheus rules and ADR-017. Alerts must include a runbook link.

**Implementation outline:**
1. Add `alert:` rules targeting `bioetl_control_plane_manifest_fail_severity_30m > 1`, `bioetl_trust_replay_blocker_events_total > 0`, etc.
2. Ensure annotations contain a `runbook_url` pointing to an existing control plane runbook (e.g., `run-manifest-inspection.md` or `workflow-control-plane.md`).

**Acceptance criteria:**
- Critical states in `bioetl_control_plane_current_status.yml` trigger Prometheus alerts.
- Alert annotations contain a valid `runbook` URL.

**Verification commands/tests:**
- Run `grep alert grafana/prometheus-rules/bioetl_control_plane_current_status.yml`
- Verify alert triggers using promtool or unit tests in `grafana/prometheus-rules/tests/`.

**Dependencies:**
None.

**Rollback/risk:**
Low risk (metrics pipeline remains unaffected, only alerting is modified). Revert the Prometheus rule changes if alert spam occurs.
