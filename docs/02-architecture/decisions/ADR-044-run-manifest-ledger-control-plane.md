______________________________________________________________________

Version: 1.1.1
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-29'

______________________________________________________________________

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
- `stage_started`
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

### 3a. Runtime execution contexts remain separate from the manifest

BioETL does not collapse runtime orchestration into one universal manifest
object.

- `PipelineRunContext` remains the canonical launch/execution descriptor used
  during runtime assembly and runner construction.
- `PipelineContext` remains the canonical in-run processing context for batch,
  writer, and post-write flows.
- `RunManifest` remains a provenance/control-plane artifact linked into those
  runtime paths via `manifest_id`, not a replacement for them.

This decision is intentional: execution context and provenance context evolve
at different seams and must remain separately testable.

### 4. File-backed persistence is the first implementation

The initial control-plane store is filesystem-backed and uses these canonical
paths:

- `data/output/control/run_manifest/{manifest_id}.json`
- `data/output/control/run_manifest/_by_run_id/{run_id}.txt`
- `data/output/control/run_ledger/{manifest_id}.jsonl`
- `data/output/control/run_ledger/_by_run_id/{run_id}.txt`

This keeps the domain/application contracts stable while leaving room for a
future SQLite or Delta projection.

### 5. Inspection is part of the published operator surface

The control plane is a supported inspection surface, not an internal-only
diagnostic appendix. The published normative pack is intentionally split:

- the **contract doc** owns storage layout, rollout-flag matrix, event
  taxonomy, and execution-path semantics;
- the **CLI reference** owns command and option inventory;
- the **runbook** owns operator procedure and triage flow;
- this **ADR** owns the decision boundary, rationale, and stable invariants.

This split is intentional and follows
[D-01](../../00-project/governance/01-documentation-governance-style-guide.md):
the ADR must not become a mutable command catalog or runtime flag registry.

### 6. Rollout semantics are governed through canonical owner docs

Runtime rollout remains governed by `settings.pipeline.control_plane`, but the
current setting matrix and profile taxonomy are documented in the published
contract and CLI surfaces rather than copied into the ADR.

The stable ADR-level invariant is fail-closed governance on the enabled path:

- no manifest, no run;
- manifest created before execution;
- manifest immutable after persistence;
- ledger append-only;
- exact replay compatibility drift is coerced to `hard_fail`; exact replay is
  not allowed to continue after compatibility drift.

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
1. Run-centric provenance can be inspected without reconstructing logs.
1. Sidecars now link upward to the control plane through `manifest_id`.
1. The model creates a stable base for future lineage and replay tooling.
1. Runtime code avoids a “one manifest for everything” god-object and keeps
   launch-time and in-run concerns separated.

### Negative

1. Additional control-plane files are written for every run.
1. Readers that only knew `run_id` must learn the `manifest_id` link.
1. File-backed inspection is simple but not optimized for large historical query workloads.

## Implementation Notes

### Current implementation boundary

The current implementation spans `domain/control_plane`, application
control-plane services, composition/runtime builders, CLI inspection commands,
and infrastructure control-plane persistence.

This ADR intentionally does **not** own a mutable file-path inventory. Current
source anchors belong in the published contract and package-level source maps so
path refactors do not stale the decision record itself.

### Execution boundary

Manifest creation is wired into runtime assembly before runner creation.
Ledger attachment happens during runner construction so lifecycle events are
appended through one shared control-plane service.

The current composite resume path uses checkpoint snapshot + ledger suffix
replay. After checkpoint anchors are validated, runtime replays only entries
strictly after `last_event_id`. This replay is intentionally coarse-grained: it
restores lifecycle milestones and replay watermark metadata without
reconstructing rich checkpoint payloads from ledger events.

The supported resume model is intentionally dual-mode:

- ordinary resume uses checkpoint snapshot state and compatibility checks
  without ledger suffix replay;
- composite resume uses checkpoint snapshot state as the base and then replays
  ledger entries strictly after `last_event_id`.
- `execution_fingerprint` remains the canonical semantic execution identity,
  while `composite_run_identity` is enforced as an occurrence-scoped resume
  anchor for composite checkpoint safety.

ADR-044 therefore does not require one universal replay algorithm across all
runner families. The stability requirement is a shared control-plane contract,
not identical resume internals.

Checkpoint incompatibility diagnostics also expose compact `current_identity`
and `checkpoint_identity` payloads so operators can explain strict resume
rejection without rehydrating the full checkpoint object.

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
