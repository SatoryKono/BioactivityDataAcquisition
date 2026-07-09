______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# Domain Control Plane

## Purpose

This page is the domain-reference catalog for the control-plane family under
`src/bioetl/domain/control_plane/`.

Use it when you need the current domain ownership map for immutable run
provenance, append-only ledger artifacts, workflow control-plane artifacts,
contract-registry types, and reproducibility policy semantics.

## Boundary

- Use [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
  for the published control-plane contract, storage layout, lifecycle policy,
  and operator-facing inspection surface.
- Use [Workflow State Machine](workflow-state-machine.md) for formal workflow
  status/transition semantics.
- Use [Domain Control Plane Artifacts](../../02-architecture/domain-control-plane.md)
  for architecture narrative and rationale.
- Use this page for the current domain catalog of the live control-plane code.

## Current Source Of Truth

- Domain package: `src/bioetl/domain/control_plane/`
- Control-plane ports: `src/bioetl/domain/ports/control_plane/`
- Accepted ADRs:
  - `ADR-044` — run manifest and run ledger control plane
  - `ADR-046` — checkpoint versus ledger-based resume
  - `ADR-047` — workflow control plane

## Catalog

| Family | Primary source files | Purpose |
| --- | --- | --- |
| Run manifest | `run_manifest.py`, `_run_manifest_serialization.py` | Immutable run intent/provenance artifact for one pipeline execution. |
| Run ledger | `run_ledger.py`, `_run_ledger_runtime.py`, `_run_ledger_serialization.py`, `_run_ledger_event_family.py`, `_run_ledger_replay_policy.py`, `run_ledger_replay.py` | Append-only run lifecycle history, event-family vocabulary, and replay projection support. |
| Workflow control plane | `workflow_manifest.py`, `workflow_ledger.py`, `workflow_execution_state.py` | Immutable workflow intent, append-only workflow history, and mutable workflow execution-state owner. |
| Effective config + execution context | `effective_config_artifact.py`, `effective_config_environment.py`, `execution_context.py`, `config_source_hashing.py` | Deterministic config identity, environment capture, and execution anchor support. |
| Contract registry + Gold contract | `contract_registry.py`, `contract_registry_helpers.py`, `contract_registry_service.py`, `contract_registry_types.py`, `gold_contract.py` | Domain ownership of contract identity, lookup, and Gold contract references. |
| Reproducibility policy | `reproducibility_policy.py`, `reproducibility_profiles.py`, `_reproducibility_profile_types.py`, `_reproducibility_profile_builders.py`, `_reproducibility_policy_profiles.py`, `_reproducibility_policy_support.py`, `_reproducibility_policy_verdicts.py` | Reproducibility classification and policy-verdict semantics. |
| Artifact lifecycle | `artifact_lifecycle.py` | Domain lifecycle decisions and protected-reference policy for control-plane artifacts. |

## High-Signal Symbol Map

Use the API reference for the full symbol list. The domain-owned symbols below
are the audit-critical anchors that must stay aligned with contracts, ADRs, and
runbooks.

| Symbol family | Representative symbols | Source |
| --- | --- | --- |
| Run manifest | `RunManifest`, `RunManifestArtifact`, `RunManifestSourceSnapshot` | `src/bioetl/domain/control_plane/run_manifest.py` |
| Run ledger | `RunLedger`, `RunLedgerEntry`, `RunLedgerReplayPolicy`, `StageCompletionUpdate` | `src/bioetl/domain/control_plane/run_ledger.py`, `_run_ledger_runtime.py`, `_run_ledger_replay_policy.py` |
| Workflow control plane | `WorkflowManifest`, `WorkflowLedger`, `WorkflowExecutionState`, `WorkflowStepState` | `src/bioetl/domain/control_plane/workflow_manifest.py`, `workflow_ledger.py`, `workflow_execution_state.py` |
| Effective config | `EffectiveConfigArtifact`, `ConfigSourceRef`, `ConfigSourceHashes`, `SourceClassProvenance` | `src/bioetl/domain/control_plane/effective_config_artifact.py`, `config_source_hashing.py` |
| Contract registry | `ContractRegistry`, `ContractRegistryEntry`, `RegistryValidationResult`, `RegistryValidationIssue` | `src/bioetl/domain/control_plane/contract_registry*.py` |
| Reproducibility | `ReproducibilityPolicy`, `ReproducibilityFamilyProfile`, `ReplayReadinessVerdict` | `src/bioetl/domain/control_plane/reproducibility*.py`, `_reproducibility_*.py` |
| Artifact lifecycle | `ControlPlaneArtifactLifecyclePolicy`, `ControlPlaneArtifactRef`, `ControlPlaneArtifactLifecyclePlan`, `ControlPlaneArtifactReplayImpact` | `src/bioetl/domain/control_plane/artifact_lifecycle.py` |

## Ownership Rules

- `RunManifest` is immutable provenance and must not be reused as mutable run
  status.
- `RunLedger` is append-only history and inspection evidence; it is not the
  mutable resume owner.
- `WorkflowManifest` is immutable workflow intent.
- `WorkflowLedger` is append-only workflow history and operator-intent
  evidence.
- `WorkflowExecutionState` is the mutable owner for workflow status, repair
  state, and ambiguity.
- Contract-registry and reproducibility surfaces are domain-owned semantic
  contracts, not infrastructure-owned file formats.

## Related Ports

Current control-plane port surface:

- `src/bioetl/domain/ports/control_plane/run_manifest.py`
- `src/bioetl/domain/ports/control_plane/run_ledger.py`
- `src/bioetl/domain/ports/control_plane/workflow_manifest.py`
- `src/bioetl/domain/ports/control_plane/workflow_ledger.py`
- `src/bioetl/domain/ports/control_plane/workflow_execution_state.py`
- `src/bioetl/domain/ports/control_plane/effective_config_artifact.py`
- `src/bioetl/domain/ports/control_plane/lineage.py`

These remain transport-neutral contracts implemented by infrastructure stores
and inspection adapters.

## Reading Order

1. Start with [Aggregates](aggregates.md) and [Invariants](invariants.md) for
   domain lifecycle rules.
2. Continue with [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
   for the published operator contract.
3. Use [Workflow State Machine](workflow-state-machine.md) for workflow status
   semantics and repair/force boundaries.
4. Use `src/bioetl/domain/control_plane/` plus the control-plane ports when
   auditing runtime ownership and DI seams.

## Related References

- [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
- [Workflow State Machine](workflow-state-machine.md)
- [Ports](ports.md)
- [Invariants](invariants.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-046](../../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md)
- [ADR-047](../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
