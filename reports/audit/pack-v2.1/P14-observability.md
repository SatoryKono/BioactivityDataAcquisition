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

No confirmed alert-coverage defect was found. The candidate `P14-OBS-001` is withdrawn: alerts in `grafana/prometheus-rules/bioetl_observability.yml` cover the source counters used by the control-plane recording rules and link to runbooks. The absence of `alert:` entries in the recording-rule file alone was insufficient evidence of a gap.

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
  - **Evidence limit**: Live Alertmanager delivery and notification routing were not exercised in this repository-only audit.

## F. Cross-cutting/root-cause clusters
- No confirmed cross-cutting defect remains from the withdrawn alert-coverage candidate.

## G. Prioritized roadmap P0→P3
- No alert-rule remediation is proposed; the existing alert group covers manifest write, ledger append, and replay reconstruction failures.

## H. Verification Matrix
- LoggerPort/MetricsPort wiring: Verified.
- Metric label cardinality: Verified.
- Signal coverage: Static alert definitions for manifest write, ledger append, and replay reconstruction are present in `bioetl_observability.yml` and reference runbooks.
- Live Alertmanager delivery / notification routing: NOT_VERIFIABLE in this repository-only audit.

## I. NOT_VERIFIABLE and missing evidence
- Live Alertmanager delivery and notification routing were not exercised; no runtime delivery claim is made.

## J. Self-check
- **Pinned revision**: Yes, ddbb7a0ee687365258bc407110e38601c4c3b765.
- **Unsupported claims**: The former claim that control-plane recording rules lack alerts has been withdrawn after checking the source-counter alert rules.
- **Stale evidence**: No, inspected at HEAD.
- **Exception handling**: Checked.
- **Score/severity consistency**: Yes.

## K. Verdict
The reviewed static evidence supports the stated metric-cardinality controls and includes runbook-linked alerts for manifest write failures, ledger append failures, and unreconstructable replay. Live alert delivery was not tested; this report makes no claim about runtime notification success.

## Issue drafts

None. The candidate alert-coverage issue was withdrawn because existing source-counter alerts cover the cited failure conditions.
