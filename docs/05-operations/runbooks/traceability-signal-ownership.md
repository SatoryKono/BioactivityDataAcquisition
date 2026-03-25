# Traceability Signal Ownership

*Last verified: 2026-03-25*

## Purpose

Define explicit ownership for operational signals so each alert has a clear path:

1. signal trigger;
2. first diagnostic command;
3. responsible owner;
4. escalation target.

This runbook complements:

- [Run Manifest Inspection](run-manifest-inspection.md)
- [Incident Response](incident-response.md)
- [Observability Checklist](observability-checklist.md)

## Canonical Correlation Anchors

All Track D diagnostics assume these anchors are present in log/event payloads
or recoverable from `run-manifest show`:

- `run_id`
- `manifest_id`
- `pipeline`
- `provider`
- `entity`
- `event_family`

When available, include:

- `dataset_ref`
- `lineage_fragment_id`
- `effective_config_hash`
- `contract_ref`
- `contract_version`

## Signal Ownership Matrix

| Signal | Trigger | Primary Owner | Backup Owner | First Command | Escalation |
|---|---|---|---|---|---|
| DQ failure rate spike | P1/P2 DQ alert, repeated `run_failed` with DQ context | Data Quality Owner | Pipeline Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Lineage gap | missing lineage fragments or sidecar mismatch | Metadata/Lineage Owner | Pipeline Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |
| Manifest missing | run exists but no manifest resolution by `run_id` | Control Plane Owner | On-call Engineer | `bioetl run-manifest show <run-id>` | Immediate P1 escalation |
| Checkpoint resume blocked | resume fails on compatibility policy (`soft_fail/hard_fail`) | Execution Owner | Control Plane Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Artifact publish linkage error | `artifact_published` exists but missing dataset/lineage links | Storage/Metadata Owner | Metadata/Lineage Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 30m unresolved |
| Composite dependency degradation | composite enrichment/cross-validation degradation signal | Composite Owner | Data Quality Owner | `bioetl run-manifest show <run-id> --format json` | Tech Lead after 45m unresolved |

## Minimal Response Contract

For each incident, owner must document in the ticket:

- `run_id`
- `manifest_id`
- affected `pipeline/provider/entity`
- `latest_status` + `latest_event_type`
- `event_family_counts`
- `artifact_refs` summary
- decision (`retry`, `quarantine`, `rollback`, `monitor`)

## Decision Guidance

Use this fast policy:

- `latest_status=failed` with missing manifest or empty ledger -> treat as
  control-plane integrity incident.
- `artifact_refs` present but `missing_artifact_links > 0` -> treat as
  traceability regression (P1 for critical datasets).
- `event_family_counts` inconsistent with success path -> run lifecycle audit
  before restart.

## Handover Notes

During ownership handover, transfer:

- known failure signatures;
- working diagnostic commands;
- expected `event_family_counts` per main scenario;
- typical false positives and suppression policy.
