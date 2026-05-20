______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-06'

______________________________________________________________________

# ADR-046: Checkpoint Versus Ledger-Based Resume

**Date:** 2026-05-06
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-010 (local-only deployment), ADR-014 (deterministic writes), ADR-015 (pipeline lifecycle), ADR-026 (composite pipeline pattern), ADR-044 (run manifest and run ledger control plane)

## Context

BioETL currently has two different control surfaces that touch resumability, but
they do not serve the same role.

- `CompositeCheckpointState` persists operational runner state such as seed,
  dependency, enricher, and merge completion markers together with strict resume
  anchors like `execution_fingerprint`, `effective_config_hash`,
  `effective_config_artifact_id`, `dq_contract_compatibility_hash`,
  `input_snapshot_fingerprint`, `contract_ref`, `contract_version`,
  `manifest_id`, and `composite_run_identity`.
- `CompositeCheckpointLoadService` validates those anchors before resume and
  fail-closes on mismatch through `CheckpointConflictError`.
- `RunLedgerEntry` and `RunLedgerService` persist append-only provenance and
  lifecycle evidence for inspection, diagnostics, and artifact linkage.
- ADR-044 already freezes the current split: ordinary resume is checkpoint-based,
  while composite resume may apply a ledger suffix strictly after
  `last_event_id`.

The open question is whether BioETL should keep this split, move resume to
ledger replay, or formalize the current hybrid as the long-term model.

Constraints that MUST remain explicit:

- BioETL is Local-Only by default (ADR-010); resume cannot assume a distributed
  orchestrator or external event store.
- Deterministic writes and exact replay anchors MUST remain aligned with
  ADR-014 and the current `execution_fingerprint` / snapshot identity model.
- Run ledger and checkpoint storage MUST NOT be casually merged because they
  serve different failure and observability roles today.
- No decision in this ADR may weaken Gold strict validation, Quarantine
  semantics, or current fail-closed exact replay behavior.

Current source-of-truth artifacts:

- `src/bioetl/application/composite/checkpoint/service.py`
- `src/bioetl/application/composite/checkpoint/load_service.py`
- `src/bioetl/application/composite/checkpoint/state.py`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/application/services/control_plane/run_ledger_service.py`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
- `docs/05-operations/runbooks/run-manifest-inspection.md`

## Current State Analysis

### 1. Checkpoint is the operational state owner

`CompositeCheckpointState` stores resumable execution facts, not merely
diagnostics:

- current FSM state;
- completed dependency/enricher sets;
- materialized `SeedResult` / `DependencyResult` / `EnrichmentResult`;
- merge completion marker;
- resume watermarks like `last_event_id` and `last_event_occurred_at`.

This means the checkpoint layer already owns the information needed to continue
execution at the correct batch/stage boundary.

### 2. Ledger is append-only provenance and replay delta, not full state

`RunLedgerReplayProjection` intentionally restores only a deterministic suffix
delta:

- lifecycle state transitions;
- `seed_completed`;
- `merge_completed`;
- last replayed event watermark.

It does **not** rebuild rich checkpoint payloads such as dependency result
maps, enrichment result maps, or merge payload details. That is a deliberate
constraint in the current implementation.

### 3. Composite resume is already hybrid, but narrowly so

`CompositeCheckpointLoadService` loads checkpoint state first, validates strict
anchors, and only then projects ledger entries strictly after `last_event_id`.
This is a bounded suffix replay used to restore lifecycle milestones after the
checkpoint baseline is trusted.

### 4. Ordinary resume is not ledger-based today

ADR-044 explicitly freezes that ordinary resume uses checkpoint state and
compatibility checks without ledger suffix replay. The project therefore does
not have one universal resume algorithm across runner families.

## Decision

Recommendation: `not now`.

BioETL SHOULD keep checkpoint state as the canonical operational resume surface
for now, and SHOULD keep RunManifest/RunLedger as provenance and inspection
surfaces. The current composite checkpoint + ledger suffix replay model MAY
remain as a bounded hybrid, but BioETL MUST NOT attempt a universal
ledger-based resume rewrite without a separate accepted implementation ADR.

This is a `not now` recommendation, not a blanket `never`.

Normative boundary:

- checkpoints remain the source of resumable execution state;
- ledger remains append-only provenance and coarse replay evidence;
- hybrid replay is allowed only where a runner already has explicit checkpoint
  state plus a proven ledger watermark contract;
- ledger MUST NOT become the default operational resume store for ordinary runs
  under this ADR.

## Comparison Matrix

| Option | Summary | Strengths | Risks / Gaps | Recommendation |
| ------ | ------- | --------- | ------------ | -------------- |
| Checkpoint as operational state, ledger as provenance | Keep current split | Smallest change, matches current code, preserves deterministic stage/batch reconstruction, keeps operator inspection separate from execution state | Two concepts remain, requires continued docs discipline | Recommended now |
| Universal ledger-based resume | Rebuild runner state from ledger events | One conceptual replay story, stronger narrative symmetry with manifest/ledger control plane | Current ledger projection is too coarse; would require new event taxonomy, richer persisted payloads, destructive replay rules, stage/batch reconstruction proofs, migration of compatibility policy | Not now |
| Hybrid everywhere | Every runner uses checkpoint baseline + ledger suffix replay | Reuses current composite pattern | Forces runners to adopt ledger watermarks even where not needed; increases coupling between operational state and provenance timeline | Not now |
| Never use ledger for resume | Checkpoint-only forever | Simplest mental model | Gives up useful bounded suffix replay for composite lifecycle recovery and watermark restoration | Not recommended |

## Risk Assessment

### Partial failure recovery

Checkpoint state already stores operational progress directly. A ledger-only
resume path would need to reconstruct equivalent state from event history and
prove that missing or duplicated lifecycle events cannot shift resume
boundaries.

### Batch boundary and offset reconstruction

Ordinary runner resume semantics depend on checkpoint compatibility anchors and
execution-specific progress state. The current ledger model does not persist a
complete, replay-safe replacement for those operational boundaries.

### Destructive replay

A ledger-driven resume model would have to define when to replay, skip, or
compensate destructive stages. ADR-044 intentionally avoids requiring one
universal replay algorithm across runner families.

### Local-only posture

Because BioETL is local-only, operational simplicity matters. A second
state-reconstruction mechanism would increase failure modes without providing a
distributed-system payoff.

### Exact replay limits

Exact replay already depends on strict input snapshots, `execution_fingerprint`,
manifest identity, and fail-closed compatibility handling. Replacing checkpoint
state with ledger replay would expand the exact-replay contract significantly.

## Consequences

### Positive

- Preserves the current fail-closed operational model with minimal ambiguity.
- Keeps `RunLedger` focused on provenance, inspection, and coarse replay
  evidence.
- Avoids a speculative architectural rewrite before state-reconstruction
  requirements are proven.
- Leaves room for future runner-specific hybrid improvements without forcing a
  universal replay contract.

### Negative

- The project must continue documenting that control-plane provenance and
  operational resume are related but not identical surfaces.
- Composite resume remains more complex than ordinary resume because it already
  uses a bounded hybrid.
- Future proposals for ledger-based resume must clear a higher evidentiary bar.

## Rollout / Migration if Ledger Resume Is Ever Selected

The follow-up implementation ADR MUST include, at minimum:

1. a complete event taxonomy sufficient to rebuild operational state, not only
   lifecycle milestones;
2. deterministic reconstruction rules for batch boundaries, offsets, and
   destructive stages;
3. compatibility semantics for partial ledgers, duplicated events, and missing
   watermarks;
4. migration rules for existing checkpoints and existing run ledgers;
5. proof that exact replay and Gold strict validation remain fail-closed.

## Compliance

| Control | Requirement | Status | Evidence |
| ------- | ----------- | ------ | -------- |
| Classification | ADR is governance-only and does not change runtime behavior directly | pass | This ADR + no production code changes |
| Architecture | Decision aligns with ADR-010, ADR-014, ADR-015, ADR-026, ADR-044 | pass | Current checkpoint/ledger split and composite hybrid are already implemented |
| Requirements | Normative guidance uses RFC 2119 language where binding | pass | Decision + follow-up sections |
| Runtime | ADR states operational impact without changing active runtime semantics | pass | `CompositeCheckpointLoadService`, `RunLedgerReplayProjection`, ADR-044 |
| Contracts | No manifest, ledger, or checkpoint schema change is introduced here | pass | Documentation-only spike |

## Rollout

- No production migration is required.
- Operator and architecture docs SHOULD point to this ADR when discussing
  checkpoint versus ledger resume semantics.
- Any later attempt to implement ledger-based resume MUST start from a new ADR
  that supersedes or amends this proposal.

## Rollback

- Rollback is documentation-only: remove or supersede this ADR if a later
  accepted ADR selects a different resume model.
- No data rollback is required because this spike does not change persisted
  contracts.

## Verification

- Run docs/runtime alignment checks for control-plane docs.
- Verify the runbook still states the dual-mode resume contract.
- Confirm no production code paths or control-plane contracts were changed by
  this spike.

## Alternatives Considered

### A. Promote RunLedger into the universal resume state immediately

Rejected for now because current ledger replay is intentionally too coarse and
does not reconstruct rich checkpoint payloads or runner-specific execution
state.

### B. Freeze checkpoint-only resume forever

Rejected because composite suffix replay already provides bounded operational
value, and the project should not forbid future evidence-backed hybrid
improvements.

### C. Treat RunManifest as the runtime resume object

Rejected because ADR-044 already separates provenance context from execution
context. `RunManifest` captures intended run identity, not mutable in-progress
execution state.

## References

- `src/bioetl/application/composite/checkpoint/service.py`
- `src/bioetl/application/composite/checkpoint/load_service.py`
- `src/bioetl/application/composite/checkpoint/state.py`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/application/services/control_plane/run_ledger_service.py`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
- `docs/05-operations/runbooks/run-manifest-inspection.md`
