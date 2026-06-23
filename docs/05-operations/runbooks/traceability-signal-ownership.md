______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-02'

______________________________________________________________________

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
1. first diagnostic command;
1. responsible owner;
1. escalation target.

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

- `artifact_id` (operator-facing alias of the published `dataset_ref`)

- `lineage_fragment_id`

- `effective_config_hash`

- `contract_ref`

- `contract_version`

- `dq_policy_ref`

- `effective_config_artifact_id`

### Signal Ownership Matrix

| Signal                           | Trigger                                                                                                                   | Primary Owner          | Backup Owner           | First Command                                     | Escalation                     |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ---------------------- | ------------------------------------------------- | ------------------------------ |
| DQ failure rate spike            | P1/P2 DQ alert, repeated `run_failed` with DQ context                                                                     | Data Quality Owner     | Pipeline Owner         | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Lineage gap                      | missing lineage fragments or sidecar mismatch                                                                             | Metadata/Lineage Owner | Pipeline Owner         | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |
| Manifest missing                 | run exists but no manifest resolution by `run_id`                                                                         | Control Plane Owner    | On-call Engineer       | `bioetl run-manifest show <run-id>`               | Immediate P1 escalation        |
| Checkpoint resume blocked        | resume fails on compatibility policy (`soft_fail/hard_fail`) or `observe_blocked_identity` on canonical identity mismatch | Execution Owner        | Control Plane Owner    | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Artifact publish linkage error   | `artifact_published` exists but missing dataset/lineage links                                                             | Storage/Metadata Owner | Metadata/Lineage Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Composite dependency degradation | composite enrichment/cross-validation degradation signal                                                                  | Composite Owner        | Data Quality Owner     | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |

### Control-plane aggregate telemetry

- Используйте `bioetl-control-plane-v1` для мониторинга aggregated manifest write failures, ledger append failures, checkpoint compatibility и control-plane read failure ratio.
- Alert `BioETLControlPlaneReadFailureRate` (runbook: `docs/05-operations/runbooks/observability-checklist.md`) сигнализирует о доле failed reads выше 5% за 30 минут, и его можно использовать как дополнительный сигнал контроля manifest/ledger integrity.

### Minimal Response Contract

- For each incident, owner must document in the ticket:

- `run_id`

- `manifest_id`

- affected `pipeline/provider/entity`

- `latest_status` + `latest_event_type`

- `event_family_counts`

- `artifact_refs` summary

- `artifact_refs[*].artifact_id` summary when present

- `correlation_anchor_gaps` snapshot

- `cross_validation_signal_present` (for composite/DQ incidents)

- decision (`retry`, `quarantine`, `rollback`, `monitor`)

### Decision Guidance

- Use this fast policy:

- `latest_status=failed` with missing manifest or empty ledger -> treat as

- control-plane integrity incident.

- `artifact_refs` / `artifact_refs[*].artifact_id` present but
  `missing_artifact_links > 0` -> treat as

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
