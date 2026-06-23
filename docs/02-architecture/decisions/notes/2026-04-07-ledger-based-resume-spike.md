______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: '@bioetl-architecture'
Reviewers:

- BioETL Team
  Last verified: '2026-04-07'

______________________________________________________________________

# Decision Note: Ledger-Based Resume Spike for Current Runtime Profile

Date: 2026-04-07
Owner: @bioetl-architecture
Related: ADR-010, ADR-014, ADR-015, ADR-026, ADR-031, ADR-044

## Question

Should BioETL replace the current checkpoint-based `--resume` model with
ledger-based resume replay in the current runtime profile?

## Confirmed Current State

### 1. Ordinary resume is checkpoint-based operational state

- `resolve_execution_offset(...)` uses `start_offset` when explicitly provided.
- Otherwise it loads checkpoint metadata and resumes from
  `records_processed`.
- This means the current ordinary runner treats checkpoint state as the source
  of truth for resumable execution offset.

### 2. Checkpoint compatibility policy already gates resume safety

- `checkpoint_compatibility_policy` is resolved from settings with
  `soft_fail` as the default.
- `CheckpointCompatibilityService` validates DQ anchors, pipeline version,
  rule bundle anchors, and execution identity.
- Policy handling is already explicit:
  - `observe`: log incompatibility and continue resume
  - `soft_fail`: block resume without crashing the process
  - `hard_fail`: raise an error and stop resume

### 3. RunManifest and RunLedger are control-plane provenance, not the primary ordinary resume state

- Manifest is created before runner assembly and before execution starts.
- Ledger is attached only after manifest creation and remains append-only.
- CLI inspection already exposes this layer through:
  - `bioetl run-manifest show`
  - `bioetl run-manifest diff`
- `build_diagnostics_summary(...)` builds operator diagnostics from
  manifest + ledger, not resumable execution state.

### 4. Composite runtime already has a narrower replay model

- Composite checkpoints remain snapshot-based.
- Composite resume may replay only the ledger suffix strictly after
  `last_event_id`.
- That replay is intentionally coarse-grained: it restores lifecycle milestones
  and replay watermark metadata, not full checkpoint payloads.

### 5. Current guarantees are already split across the right seams

- Checkpoint: resumable operational state.
- Checkpoint compatibility policy: resume safety gate.
- Manifest: immutable launch/provenance snapshot.
- Ledger: append-only lifecycle history and inspection evidence.

For the Local-Only, single-instance, file-backed runtime, this already gives:

- deterministic ordinary resume offset handling;
- explicit compatibility gating before resume;
- provenance and inspection without reconstructing logs;
- coarse replay support only where composite checkpoints need it.

## What Full Ledger-Based Resume Would Require

### 1. A different source of truth for execution state

Ledger-based resume for ordinary runs would require a decision that the ledger,
not checkpoint state, becomes the authoritative source for:

- execution offset;
- stage progress;
- retry/shutdown recovery position;
- any provider-specific continuation semantics.

That is not how the current runtime is modeled.

### 2. A richer event stream than the current baseline

The current ledger baseline is lifecycle-oriented:

- `manifest_created`
- `run_started`
- `stage_started`
- `stage_completed`
- `artifact_published`
- `run_finished`
- `run_failed`
- `run_shutdown`
- `dq_policy_applied`

This baseline is good for provenance and diagnostics, but not sufficient as a
general resumable state log for ordinary runners. A full ledger-based resume
model would need deterministic event coverage for:

- offset or cursor advancement;
- partial batch progress;
- provider-specific pagination anchors;
- shutdown-safe replay cut points;
- idempotent write boundaries.

That would be a semantic redesign of the control-plane contract, not a small
wiring change.

### 3. A projector model for ordinary and composite execution

BioETL would need a stable projector that can reconstruct resumable execution
state from the event stream alone.

That implies:

- replay ordering invariants stronger than the current append-only contract;
- explicit replay schema/versioning policy;
- compatibility rules for old event histories;
- deterministic projection across ordinary and composite runners.

### 4. Composite checkpoint semantics would need redesign, not just reuse

Today composite resume uses:

- checkpoint snapshot as the base;
- ledger suffix replay only after `last_event_id`.

If ledger became the universal resume source of truth, BioETL would need to
decide whether to:

- remove rich composite checkpoint payloads entirely; or
- keep checkpoint payloads and create dual operational truth sources.

Both options increase complexity.

### 5. Failure, retry, and shutdown semantics would get stricter

A ledger-driven resume model would need to define, test, and document:

- how failed runs reconstruct the last safe offset;
- how shutdown differs from failure in replay semantics;
- how retries avoid duplicate writes after partial publication;
- what happens when the ledger is incomplete or truncated;
- whether replay can continue after control-plane corruption.

The current checkpoint model already answers these questions in a smaller and
more operationally direct way.

### 6. CLI, runbook, migration, and rollback impact

Ledger-based resume would also require changes to:

- CLI help and operator wording around `--resume`;
- runbooks and troubleshooting flow;
- contract docs and architecture docs;
- migration of existing checkpoint-only historical runs;
- rollback strategy when replay projection fails in the field.

This is compatibility-sensitive because current docs intentionally freeze the
ordinary/composite split.

## Trade-Off Comparison

| Model                                               | Value                                                                                                                                             | Migration cost                                                                                 | Operational risk                                                                                 | Compatibility impact                                                                   |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Checkpoint = operational state, ledger = provenance | High for current Local-Only profile because it is already implemented, simple, and operator-comprehensible                                        | Low incremental cost because it matches current main                                           | Low to moderate; failure domain is limited to checkpoint state and existing compatibility policy | Low; aligns with current CLI, docs, tests, and published contract                      |
| Ledger = source of resumable execution state        | Low to moderate near-term value in current profile because manifest/ledger already solve provenance and inspection, not missing operational state | High; requires new event completeness rules, projector semantics, migration, and rollback plan | High; replay bugs would affect resume correctness, duplicate work, and operator trust            | Medium to high; changes published control-plane semantics and ordinary resume contract |

## Recommendation

### recommended now

Keep the current model:

- checkpoint remains the source of resumable operational state;
- checkpoint compatibility policy remains the gate for `--resume`;
- manifest and ledger remain provenance, inspection, and diagnostics layers;
- composite suffix replay remains the only replay-enabled resume path.

### not now

Revisit ledger-based resume only if the runtime profile changes materially, for
example:

- Local-Only no longer holds;
- single-instance execution no longer holds;
- file-backed control-plane is replaced by a shared durable projection store;
- checkpoint state proves operationally insufficient for real workloads.

That future discussion should be a dedicated ADR, not a hidden extension of
ADR-044.

### never for current runtime profile

For the current Local-Only, single-instance, file-backed runtime profile, BioETL
SHOULD NOT replace ordinary checkpoint resume with ledger replay.

The current profile gains little new value from that migration while taking on
material migration cost, operational risk, and compatibility churn.

## Explicit Evaluation

- Value: low-to-moderate incremental value now; most provenance/inspection value
  is already delivered by manifest + ledger without changing resume semantics.
- Migration cost: high; requires event-model expansion, projector design,
  compatibility rules, migration, and rollback choreography.
- Operational risk: high; replay correctness becomes part of resume correctness.
- Compatibility impact: medium-to-high; published docs currently freeze
  checkpoint-based ordinary resume and checkpoint-plus-ledger-suffix composite
  resume.

## Outcome

This spike recommends keeping the current intentional split:

- ordinary resume = checkpoint operational state;
- ledger = provenance and inspection;
- composite replay = narrow checkpoint suffix recovery helper, not a universal
  event-sourced runtime.
