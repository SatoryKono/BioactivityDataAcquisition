---
Version: 1.1.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-01'
---

# ADR-044: Run Manifest and Run Ledger Control Plane

**Date:** 2026-03-24
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-014 (deterministic writes), ADR-015 (pipeline lifecycle), ADR-029 (output metadata), ADR-043 (documentation governance), ADR-045 (DQ contract system)

## Context

BioETL already captured useful provenance fragments during execution:

- `RunContext` stored `pipeline_version`, `git_commit`, and `config_hash`;
- Bronze/Silver/Gold sidecars stored runtime and lineage metadata;
- `PipelineRun` modeled in-process lifecycle transitions.

However, those facts were distributed across multiple layers and were not
persisted as one immutable control-plane artifact. As a result, reproducibility
remained partial:

- a run could be identified by `run_id`, but not by one canonical manifest;
- incident/debug workflows had to reconstruct provenance from logs and sidecars;
- it was hard to distinguish exact replay of the same resolved launch from a new
  run that happened to write to the same destinations.

## Decision

BioETL introduces a dedicated control-plane family with two different roles.

### 1. `RunManifest` is immutable

`RunManifest` captures what was intended to run:

- `manifest_id`
- `run_id`
- `execution_fingerprint`
- pipeline/provider/entity identity
- resolved runtime/config snapshot
- code provenance (`pipeline_version`, `git_commit`, `config_hash`)
- source references
- planned artifact references

The manifest is created and persisted before runner assembly and execution
begins.

### 2. `RunLedgerEntry` is append-only

`RunLedgerEntry` records what actually happened during lifecycle. The current
inspection baseline includes:

- `manifest_created`
- `run_started`
- `stage_completed`
- `artifact_published`
- `run_finished`
- `run_failed`
- `run_shutdown`
- `dq_policy_applied`

### 3. `manifest_id` links execution-local projections

`RunContext`, `PipelineRunContext`, runtime sidecar metadata, lineage fragments,
and inspection CLI carry `manifest_id` as a reference. They do not embed the
full manifest.

### 4. File-backed persistence is the first implementation

The initial control-plane store is filesystem-backed and uses these canonical
paths:

- `data/output/control/run_manifest/{manifest_id}.json`
- `data/output/control/run_manifest/_by_run_id/{run_id}.txt`
- `data/output/control/run_ledger/{manifest_id}.jsonl`
- `data/output/control/run_ledger/_by_run_id/{run_id}.txt`

This keeps the domain/application contracts stable while leaving room for a
future SQLite or Delta projection.

### 5. Inspection is part of the supported CLI

The control plane is inspectable via:

- `bioetl run-manifest show <run-id|manifest-id>`
- `bioetl run-manifest diff <left> <right>`

`show` resolves to one payload with `manifest`, `ledger_entries`, and
operator-oriented `diagnostics`. `diff` compares top-level manifest fields
after canonical JSON normalization.

This inspection surface is a published documentation surface, not an
internal-only diagnostic appendix. The normative pack is ADR + contract + CLI +
runbook, following [D-01](../../00-project/governance/01-documentation-governance-style-guide.md).

### 6. Rollout is governed by explicit control-plane settings

The supported rollout flags are:

- `run_manifest_enabled=true`
- `run_ledger_enabled=true`
- `checkpoint_compatibility_policy=soft_fail`

`run_ledger_enabled` depends on `run_manifest_enabled`, and checkpoint resume
behavior is constrained to `observe | soft_fail | hard_fail`.

### 7. Governance is fail-closed on the enabled path

The enabled control-plane path follows these invariants:

- no manifest, no run;
- manifest created before execution;
- manifest immutable after persistence;
- ledger append-only;
- sidecars reference `manifest_id` instead of embedding manifest.

## Consequences

### Positive

1. Each run becomes a globally addressable reproducibility object.
2. Run-centric provenance can be inspected without reconstructing logs.
3. Sidecars now link upward to the control plane through `manifest_id`.
4. The model creates a stable base for future lineage and replay tooling.

### Negative

1. Additional control-plane files are written for every run.
2. Readers that only knew `run_id` must learn the `manifest_id` link.
3. File-backed inspection is simple but not optimized for large historical query workloads.

## Implementation Notes

### Canonical code locations

- `src/bioetl/domain/control_plane/`
- `src/bioetl/domain/ports/control_plane/`
- `src/bioetl/application/services/run_manifest_service.py`
- `src/bioetl/application/services/run_ledger_service.py`
- `src/bioetl/application/services/run_manifest_diagnostics.py`
- `src/bioetl/application/services/run_manifest_inspection_service.py`
- `src/bioetl/application/core/lifecycle/checkpoint_runtime.py`
- `src/bioetl/interfaces/cli/commands/run_manifest.py`
- `src/bioetl/composition/bootstrap/cli/run_manifest.py`
- `src/bioetl/composition/runtime_builders/run_manifest_builder.py`
- `src/bioetl/composition/runtime_builders/runner_builder.py`
- `src/bioetl/composition/factories/pipeline/checkpoint_policy_helpers.py`
- `src/bioetl/infrastructure/config/_base.py`
- `src/bioetl/infrastructure/control_plane/`

### Execution boundary

Manifest creation is wired into runtime assembly before runner creation.
Ledger attachment happens during runner construction so lifecycle events are
appended through one shared control-plane service.

## Compliance

- Reproducibility and deterministic execution: ADR-014
- Lifecycle boundaries and shutdown behavior: ADR-015
- Sidecar metadata linkage: ADR-029
- Documentation publication and runbook indexing: ADR-043

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [x] ADR, contract, CLI, and runbook are aligned.
- [x] Storage layout, flags, event names, and invariants match the active runtime.
- [x] Inspection commands are reproducible for operators.
- [x] Related navigation and governance docs point to the current control-plane pack.

## References

- [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
- [CLI Reference](../../04-reference/cli.md)
- [Run Manifest Inspection Runbook](../../05-operations/runbooks/run-manifest-inspection.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../../00-project/00-map.md)
