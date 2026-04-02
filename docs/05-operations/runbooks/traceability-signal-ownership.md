---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Priority: P1
Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
Last verified: '2026-04-02'
---

# Traceability Signal Ownership

## Trigger

- Run this procedure when operators need the owner, routing, and escalation contract for traceability signals.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Purpose

- Define explicit ownership for operational signals so each alert has a clear path:

1. signal trigger;
2. first diagnostic command;
3. responsible owner;
4. escalation target.

- This runbook complements:

- [Run Manifest Inspection](run-manifest-inspection.md)
- [Incident Response](incident-response.md)
- [Observability Checklist](observability-checklist.md)
- [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)

### Role Boundary

- This page is the ownership and escalation reference.
- Use [Traceability Tabletop Drills](traceability-tabletop-drills.md) for the
  recurring drill catalog and scoring model.
- Use [Traceability Adoption Checklist](traceability-adoption-checklist.md) for
  readiness evidence and exit-gate tracking.
- Use [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)
  as the canonical execution pack for the final manual gate.

### Canonical Correlation Anchors

- All Track D diagnostics assume these anchors are present in log/event payloads or recoverable from `run-manifest show`:

- `run_id`
- `manifest_id`
- `pipeline`
- `provider`
- `entity`
- `event_family`

- When available, include:

- `dataset_ref`
- `lineage_fragment_id`
- `effective_config_hash`
- `contract_ref`
- `data_contract_version`
- `dq_policy_ref`
- `effective_config_artifact_id`

### Signal Ownership Matrix

| Signal | Trigger | Primary Owner | Backup Owner | First Command | Escalation |
|---|---|---|---|---|---|
| DQ failure rate spike | P1/P2 DQ alert, repeated `run_failed` with DQ context | Data Quality Owner | Pipeline Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Lineage gap | missing lineage fragments or sidecar mismatch | Metadata/Lineage Owner | Pipeline Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |
| Manifest missing | run exists but no manifest resolution by `run_id` | Control Plane Owner | On-call Engineer | `bioetl run-manifest show <run-id>` | Immediate P1 escalation |
| Checkpoint resume blocked | resume fails on compatibility policy (`soft_fail/hard_fail`) | Execution Owner | Control Plane Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Artifact publish linkage error | `artifact_published` exists but missing dataset/lineage links | Storage/Metadata Owner | Metadata/Lineage Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Composite dependency degradation | composite enrichment/cross-validation degradation signal | Composite Owner | Data Quality Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |

### Minimal Response Contract

- For each incident, owner must document in the ticket:

- `run_id`
- `manifest_id`
- affected `pipeline/provider/entity`
- `latest_status` + `latest_event_type`
- `event_family_counts`
- `artifact_refs` summary
- `correlation_anchor_gaps` snapshot
- `cross_validation_signal_present` (for composite/DQ incidents)
- decision (`retry`, `quarantine`, `rollback`, `monitor`)

### Decision Guidance

- Use this fast policy:

- `latest_status=failed` with missing manifest or empty ledger -> treat as
- control-plane integrity incident.
- `artifact_refs` present but `missing_artifact_links > 0` -> treat as
- traceability regression (P1 for critical datasets).
- `cross_validation_signal_present=true` -> involve Composite Owner + DQ Owner
- before retry.
- `event_family_counts` inconsistent with success path -> run lifecycle audit
- before restart.

### Handover Notes

- During ownership handover, transfer:

- known failure signatures;
- working diagnostic commands;
- expected `event_family_counts` per main scenario;
- typical false positives and suppression policy.

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
