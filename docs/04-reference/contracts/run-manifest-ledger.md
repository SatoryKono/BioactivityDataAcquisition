______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: "2026-04-23"

______________________________________________________________________

# Run Manifest and Run Ledger Contract

## Purpose

This document defines the published control-plane contract for immutable run
manifests, append-only run ledgers, and the inspection surface used by
operators and diagnostics.

Current published scope: BioETL supports strict exact replay only inside the
explicitly published snapshot-backed support boundary. The platform does not
currently claim universal exact reproducibility for every pipeline family and
every historical run occurrence.

It is the contract leg of the published traceability documentation pack
required by [D-01](../../00-project/governance/01-documentation-governance-style-guide.md).

The current code owners / source-of-truth seams are:

- `src/bioetl/domain/control_plane/run_manifest.py`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/domain/ports/control_plane/`
- `src/bioetl/application/services/control_plane/run_manifest_service.py`
- `src/bioetl/application/services/control_plane/run_ledger_service.py`
- `src/bioetl/application/services/control_plane/run_manifest_diagnostics.py`
- `src/bioetl/application/services/control_plane/run_manifest_inspection_service.py`
- `src/bioetl/application/core/lifecycle/checkpoint_runtime.py`
- `src/bioetl/application/composite/checkpoint/load_service.py`
- `src/bioetl/interfaces/cli/commands/run_manifest.py`
- `src/bioetl/composition/bootstrap/cli/run_manifest.py`
- `src/bioetl/composition/runtime_builders/run_manifest_builder.py`
- `src/bioetl/composition/runtime_builders/runner_builder.py`
- `src/bioetl/composition/factories/pipeline/checkpoint_policy_helpers.py`
- `src/bioetl/infrastructure/config/_base.py`
- `src/bioetl/infrastructure/control_plane/`

## Execution Context Boundary

The published control-plane contract does not replace BioETL runtime execution
contexts.

- `PipelineRunContext` remains the canonical launch/execution descriptor used
  by composition/runtime assembly before a runner starts.
- `PipelineContext` remains the canonical in-run processing context used by
  record, batch, write, and post-write flows.
- `RunManifest` remains an immutable provenance/control-plane artifact linked
  to runtime execution via `manifest_id`.

This means the supported model is deliberately split. BioETL does not define
one universal manifest object that serves as launch descriptor, in-run context,
and provenance artifact at the same time.

## Storage Layout

File-backed control-plane persistence uses the following canonical paths:

| Artifact                             | Path                                                               |
| ------------------------------------ | ------------------------------------------------------------------ |
| Manifest payload                     | `data/output/control/run_manifest/{manifest_id}.json`              |
| Manifest run-id index                | `data/output/control/run_manifest/_by_run_id/{run_id}.txt`         |
| Ledger payload                       | `data/output/control/run_ledger/{manifest_id}.jsonl`               |
| Ledger run-id index                  | `data/output/control/run_ledger/_by_run_id/{run_id}.txt`           |
| Effective config semantic artifact   | `data/output/control/effective_config/{artifact_id}.json`          |
| Effective config occurrence envelope | `data/output/control/effective_config/_occurrences/{run_id}.json`  |
| Effective config run-id index        | `data/output/control/effective_config/_by_run_id/{run_id}.txt`     |
| Lineage fragment payload             | `data/output/control/lineage/fragments/{stable_fragment_key}.json` |
| Lineage lookup indexes               | `data/output/control/lineage/_by_*/*.jsonl`                        |
| Checkpoint payloads                  | `data/output/checkpoints/**/*.json`                                |
| Cached Bronze input snapshots        | `data/output/bronze/**/*`                                          |

`run_manifest` and `run_ledger` stores are bootstrapped from
`Path(settings.data_dir) / "output" / "control" / <leaf>` and are therefore
runtime-aligned with the current composition layer.

## Lifecycle Management

File-backed control-plane lifecycle management is planner-driven:

- `ControlPlaneArtifactLifecyclePolicy` declares the retention window, planning
  timestamp, and explicit protected references.
- `FileControlPlaneArtifactLifecycleStore.plan(..., dry_run=True)` returns a
  complete dry-run plan and MUST NOT delete files.
- `FileControlPlaneArtifactLifecycleStore.plan(..., dry_run=False)` returns the
  same decision model for apply mode.
- `FileControlPlaneArtifactLifecycleStore.apply(plan)` deletes only artifacts
  whose plan decision is `delete`; dry-run plans are no-op during apply.

Protected-reference rules are fail-closed:

- manifests inside the retention window protect their `manifest_id`, `run_id`,
  `replay_of_manifest_id`, and
  `code_provenance.effective_config_artifact_id`;
- manifests inside the retention window protect content-addressed
  `source_refs[*].input_snapshots[*].snapshot_id` values;
- stale manifests that declare `required_persistence_profile=replay_ready` or
  `required_persistence_profile=forensic_grade` retain their replay evidence
  floor unless `ControlPlaneArtifactLifecyclePolicy.allow_profile_floor_violation`
  is explicitly enabled;
- checkpoints inside the retention window protect their `run_id`,
  `manifest_id`, and `effective_config_artifact_id` anchors;
- explicit protected manifest/run/effective-config/lineage/snapshot identifiers
  protect matching payloads and lookup indexes regardless of age;
- ledgers are retained when their `manifest_id` or `run_id` is protected;
- effective-config semantic artifacts are retained when referenced by a
  protected or retention-active manifest;
- effective-config occurrence envelopes and run indexes are retained when their
  `run_id` is protected;
- lineage fragments are retained when their `manifest_id`, `run_id`,
  `stored_fragment_id`, or semantic `fragment_id` is protected.
- cached Bronze files are retained when their `sha256:{content_hash}` identity
  is protected by a retained manifest or explicit snapshot protection.
- profile-floor retention is emitted as
  `reason=reproducibility_evidence_floor` with `protected_by` entries prefixed
  by `evidence_floor:` so dry-run/apply output distinguishes replay evidence
  violations from ordinary protected references.

Lifecycle planning is intentionally independent from read APIs: expired
unprotected files can be selected for deletion even if higher-level lookup
indexes are already orphaned. Corruption-visible read paths still fail closed
before lifecycle apply is considered.

## Rollout Flags

The control-plane runtime is governed by the runtime object path
`settings.pipeline.control_plane`. The source-of-truth model is
`PipelineSettings.ControlPlaneSettings` in
`src/bioetl/infrastructure/config/_base.py`.

| Setting                           |               Default | Effect                                                                                                                         |
| --------------------------------- | --------------------: | ------------------------------------------------------------------------------------------------------------------------------ |
| `required_persistence_profile`    | `degraded_observable` | Minimum control-plane persistence contract required for this runtime (`degraded_observable`, `replay_ready`, `forensic_grade`) |
| `run_manifest_enabled`            |                `true` | Create immutable manifest before runner assembly / execution starts                                                            |
| `run_ledger_enabled`              |                `true` | Append lifecycle and inspection events keyed by `manifest_id`                                                                  |
| `checkpoint_compatibility_policy` |           `soft_fail` | Resume behavior when checkpoint identity mismatches runtime (`observe`, `soft_fail`, `hard_fail`, `legacy_observe`)            |

Current rollout semantics:

1. `run_manifest_enabled=false` disables both manifest creation and ledger attachment for new runs because runtime assembly coerces the effective flag set to `(False, False)`.
1. `run_manifest_enabled=true`, `run_ledger_enabled=false` keeps manifest creation but suppresses ledger writes.
1. `run_ledger_enabled=true` is only valid when `run_manifest_enabled=true`.
1. Supported production and debug-critical launches inherit the published
   family default when the configured profile remains
   `degraded_observable`. For snapshot-backed supported source families and
   composite launches this effective default is `replay_ready`.
1. The effective default is fail-closed: a production/debug-critical supported
   family launch that cannot prove immutable input snapshots, or a composite
   launch without a full snapshot envelope, is blocked before it can be claimed
   as replay-ready.
1. `required_persistence_profile=replay_ready` requires
   `run_manifest_enabled=true` and an execution context inside the published
   strict exact-replay support boundary.
1. `required_persistence_profile=forensic_grade` requires both
   `run_manifest_enabled=true` and `run_ledger_enabled=true`, plus replay-ready
   and lineage-closure surfaces inside the same published support boundary.
1. `checkpoint_compatibility_policy` governs resume disposition on checkpoint incompatibility:
   `observe` remains a degraded operator mode for non-identity signals, but canonical
   execution-identity mismatches still block resume; `soft_fail` blocks resume;
   `hard_fail` raises an error; `legacy_observe` remains a legacy degraded mode
   for v1.x-era migration periods but does not permit resume when identity
   continuity is unproven.
1. `exact_replay=true` is stricter than the requested compatibility policy:
   runtime coerces checkpoint compatibility handling to `hard_fail` so an
   exact replay attempt cannot continue after any compatibility mismatch.

## Checkpoint Compatibility Policy

The BioETL control-plane supports four checkpoint compatibility modes that govern
resume behavior when checkpoint identity mismatches occur:

### Policy Enum

```python
# src/bioetl/application/core/lifecycle/checkpoint_runtime.py
CheckpointCompatibilityPolicy = Literal[
    "observe", "legacy_observe", "soft_fail", "hard_fail"
]
```

### Policy Semantics

| Policy           | Behavior                                                                                                                                | Use Case                                           | Default         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | --------------- |
| `observe`        | Resume only after non-identity compatibility warnings; canonical execution-identity mismatch still blocks resume                        | Operator-aware degraded mode outside strict replay | ❌ Manual       |
| `soft_fail`      | Block resume on incompatibility without aborting the whole process                                                                      | Default fail-closed resume behavior                | ✅ Default      |
| `hard_fail`      | Halt pipeline by raising on incompatibility                                                                                             | Critical integrity and exact replay                | ✅ Exact replay |
| `legacy_observe` | Legacy degraded mode for migration periods; may tolerate non-identity degradation but still blocks when identity continuity is unproven | Temporary migration periods only                   | ❌ Manual       |

### Decision Flow

```mermaid
graph TD
    A[Checkpoint Mismatch Detected] --> B{Compatibility Policy}
    B -->|observe| C{Canonical execution identity mismatched?}
    C -->|yes| D[Block Resume]
    C -->|no| E[Log Warning\nResume Only After Non-identity Degradation]
    B -->|soft_fail| D
    B -->|hard_fail| H[Halt Pipeline\nRaise Error]
    B -->|legacy_observe| F{Identity continuity proven?}
    F -->|no| D
    F -->|yes| G[Legacy Validation\nResume Only For Non-identity Degradation]
```

### Configuration

```yaml
# configs/entities/provider/entity.yaml
runtime:
  checkpoint_compatibility:
    critical: hard_fail      # Default for critical operations
    non_critical: observe    # Default for non-critical operations
    migration_mode: legacy_observe  # Temporary during version upgrades
```

### Policy Selection Guide

**Use `observe` when:**

- Non-critical validation scenarios
- Development/testing environments
- Graceful degradation is acceptable

**Use `soft_fail` when:**

- Default operator-facing fail-closed resume behavior
- Recovery scenarios where incompatibility should block resume without aborting
  the whole process
- Strict persistence profiles below `exact_replay` minimum coercion

**Use `hard_fail` when:**

- Critical integrity requirements
- Production steady-state
- Exact replay requirements

**Use `legacy_observe` when:**

- A temporary migration window still needs legacy checkpoint compatibility
  diagnostics
- Mixed-version or mixed-format recovery is being retired in a controlled way
- You still want identity-continuity failures to block resume

### Migration Procedure

1. **Prepare**: Set `legacy_observe` in configuration
1. **Upgrade**: Roll out new version nodes incrementally
1. **Validate**: Monitor validation warnings in logs
1. **Remove**: Switch to standard modes after full upgrade
1. **Cleanup**: Remove legacy mode from configurations

## Supported Resume Modes

The current control-plane contract intentionally supports two different resume
modes:

- ordinary resume uses checkpoint snapshot state and compatibility checks
  without ledger suffix replay;
- composite resume uses checkpoint snapshot state as the base and then replays
  only the ledger suffix strictly after `last_event_id`.
- `execution_fingerprint` remains the canonical semantic execution identity,
  while `composite_run_identity` is an occurrence-scoped resume anchor used to
  block composite checkpoint drift across logically different executions.

This asymmetry is intentional. The current contract finishes the existing
composite replay model without requiring every runner to implement the same
ledger-driven state projection.

## Supported Execution Paths

The current control-plane contract is defined against these supported execution
paths:

| Path                 | Resume model                               | Control-plane guarantees                                                                                                                                                                                                 |
| -------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ordinary success`   | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, `run_started`, stage lifecycle events, and `run_finished` when ledger is enabled                                                              |
| `ordinary failure`   | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, `run_started`, partial stage lifecycle events, and terminal failure semantics through `run_failed` / exception logging when ledger is enabled |
| `ordinary shutdown`  | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, `run_started`, partial stage lifecycle events, and `run_shutdown` when ledger is enabled                                                      |
| `ordinary resume`    | checkpoint snapshot only                   | Manifest still exists before execution starts; resume relies on checkpoint snapshot state and compatibility checks without ledger suffix replay                                                                          |
| `composite success`  | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, composite lifecycle events, and terminal success when ledger is enabled                                                                       |
| `composite failure`  | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, composite lifecycle events, and terminal failure semantics when ledger is enabled                                                             |
| `composite shutdown` | none                                       | Manifest exists before execution starts; ledger writes `manifest_created`, composite lifecycle events, and `run_shutdown` when ledger is enabled                                                                         |
| `composite resume`   | checkpoint snapshot + ledger suffix replay | Manifest still exists before execution starts; resume restores checkpoint snapshot first and then replays only the ledger suffix strictly after `last_event_id`                                                          |

No supported execution path may bypass manifest creation or, when
`run_ledger_enabled=true`, ledger attachment. Runtime assembly coerces invalid
flag combinations so that ledger cannot be enabled without manifest creation.

## Composite Checkpoint Resume Semantics

The current replay-enabled resume path is implemented for composite checkpoints.

- checkpoint state remains snapshot-only;
- the composite checkpoint snapshot carries replay watermark metadata through
  `last_event_id` and `last_event_occurred_at`;
- composite checkpoint compatibility also enforces
  `composite_run_identity` as an occurrence-scoped anchor distinct from the
  semantic `execution_fingerprint`;
- after the checkpoint snapshot is loaded and compatibility anchors are
  validated, runtime replays only the ledger suffix strictly after
  `last_event_id` via `RunLedgerPort.list_entries_after(manifest_id, last_event_id)`;
- the replay projector is intentionally coarse-grained: it restores lifecycle
  milestones such as `state`, `seed_completed`, `merge_completed`, and the
  latest replay watermark, but does not fabricate rich checkpoint payloads such
  as per-provider result maps;
- if the replay watermark is missing from the append order for the current
  `manifest_id`, runtime treats this as checkpoint incompatibility and raises a
  checkpoint conflict instead of silently continuing.

## Persistence Profile Evaluation

Inspection diagnostics classify each resolved run against one explicit
persistence-profile taxonomy:

- `forensic_grade`: the run is replay-ready and also retains ledger-backed
  control-plane history plus complete artifact/lineage anchors for published
  outputs within the currently supported lineage-closure boundary;
- `replay_ready`: immutable input snapshots, exact-replay capability, and the
  effective-config artifact anchor are present, but richer forensic surfaces may
  still be absent;
- `degraded_observable`: the run remains inspectable through the persisted
  manifest, but one or more mandatory replay-ready requirements are missing.

`required_persistence_profile` is the declared minimum profile requested by the
runtime/deployment for that run. The current published contract is:

- `degraded_observable` is always the floor and may still be inspected even
  when richer replay/forensic surfaces are absent;
- `replay_ready` is only valid inside the strict exact-replay support boundary;
  execution contexts outside that boundary must fail closed during bootstrap
  instead of running and merely reporting a degraded profile later. For
  ordinary source runs this also requires immutable input snapshots and
  `exact_replay_capability` on the built manifest request for the current run;
- outside that published support boundary the contract is intentionally
  narrower: the platform guarantees inspectable degraded observability, not
  universal exact replay for every run;
- `forensic_grade` requires `replay_ready` surfaces plus append-only ledger
  history and metadata-sidecar / lineage persistence for every active published
  layer in the configured sink surface.

The current diagnostics surface exposes:

- `persistence_profile.attained_profile`;
- `persistence_profile.required_profile`;
- `persistence_profile.required_profile_satisfied`;
- `lineage_closure_boundary.family`;
- `lineage_closure_boundary.supported`;
- `lineage_closure_boundary.reason`;
- `persistence_profile.required_profile_missing_requirements`;
- `persistence_profile.claims`;
- `persistence_profile.surfaces`;
- `persistence_profile.replay_ready_missing_requirements`;
- `persistence_profile.forensic_grade_missing_requirements`.
- `alert_signals.immutable_input_snapshot_gap`;
- `alert_signals.composite_resume_reconstructability_gap`;
- `alert_signals.required_persistence_profile_gap`;
- `alert_signals.replay_ready_gap`;
- `alert_signals.forensic_grade_gap`;
- `alert_signals.lineage_closure_boundary_gap`;

When ledger-backed diagnostics are available, these profile gaps are promoted
into alert-oriented booleans and operator next steps so replay/forensic
deficiencies are visible as actionable signals rather than passive metadata.
When immutable input snapshots are the missing replay-ready requirement, the
diagnostics surface raises `alert_signals.immutable_input_snapshot_gap` and
points the operator back to cached-Bronze snapshot persistence before exact
replay can be claimed.

## Reproducibility Scoring Rubric

The profile taxonomy above is the authority for pass/fail behavior. The
following score is an operator-facing evidence summary; it does not override
`required_persistence_profile` or exact-replay bootstrap checks.

| Score | Label                 | Required evidence                                                                 |
| ----: | --------------------- | --------------------------------------------------------------------------------- |
|     0 | `not_observable`      | No manifest can be resolved for the run or manifest identifier                    |
|    25 | `manifest_observable` | Manifest resolves and exposes execution identity plus runtime/config provenance   |
|    50 | `ledger_observable`   | Manifest plus append-only ledger history are available and corruption-visible     |
|    75 | `replay_ready`        | Immutable input snapshots and effective-config artifact anchors support replay    |
|   100 | `forensic_grade`      | Replay-ready evidence plus lineage/artifact closure inside the supported boundary |

Evidence matrix:

| Evidence surface                   | Degraded observable | Replay ready | Forensic grade |
| ---------------------------------- | ------------------: | -----------: | -------------: |
| Manifest payload                   |            required |     required |       required |
| Execution fingerprint              |            required |     required |       required |
| Effective-config semantic artifact |            optional |     required |       required |
| Immutable input snapshot refs      |            optional |     required |       required |
| Append-only ledger                 |            optional |     optional |       required |
| Artifact linkage diagnostics       |            optional |     optional |       required |
| Lineage closure boundary           |            optional |     optional |       required |
| Supported reproducibility family   |            optional |     required |       required |

Evidence scoring is conservative: a missing mandatory surface caps the score
at the highest lower tier whose evidence is complete, and unsupported lineage
families cannot score above `replay_ready`.

The repeatable audit rubric is maintained in
[Reproducibility Scoring Rubric](reproducibility-scoring-rubric.md). It defines
the required seven categories, five criteria per category, and the 0/1/2 scoring
semantics reviewers must cite when recalculating audit scores.

Composite replay is additionally documented as a bounded reconstructability
surface:

- scope: `coarse_grained_composite_resume`;
- resume model: `checkpoint_snapshot_plus_ledger_suffix`;
- reconstructed from persisted state: `state`, `seed_completed`,
  `merge_completed`, `last_event_id`, `last_event_occurred_at`;
- not reconstructed: per-provider result maps and other rich checkpoint
  payloads.

When the inspected execution context is composite, diagnostics also raise
`alert_signals.composite_resume_reconstructability_gap` and point operators to
the bounded replay contract instead of implying richer checkpoint-state
reconstruction.

Checkpoint incompatibility diagnostics also expose two compact forensic payloads:

- `current_identity`
- `checkpoint_identity`

These payloads intentionally surface the resume-critical anchors
(`composite_run_identity`, `execution_fingerprint`, `manifest_id`,
`effective_config_hash`, `contract_ref`, `contract_version`, `exact_replay`,
`input_snapshot_ids`) so operators can explain why resume was rejected or
degraded without inspecting the full checkpoint blob first.

## Observability & Metrics

- Aggregated control-plane telemetry lives in `grafana/dashboards/bioetl-control-plane-v1.json`.
  Этот dashboard показывает manifest write failures, ledger append failures,
  checkpoint compatibility incompatibilities и read failure ratio scoped по
  `$pipeline/$run_type`.
- Alert `BioETLControlPlaneReadFailureRate` (see `docs/05-operations/runbooks/observability-checklist.md`)
  сигнализирует, когда доля failed control-plane reads по store/operation
  превышает 5% за 30 минут и служит дополнительной точкой входа для traceability incidents.

## Run Manifest Contract

`RunManifest` is immutable and captures launch-time intent plus reproducibility
provenance.

| Field                   | Type       | Required | Notes                                                                                                                                                                         |
| ----------------------- | ---------- | -------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest_id`           | `str`      |      yes | Stable identifier of the manifest record                                                                                                                                      |
| `execution_fingerprint` | `str`      |      yes | Canonical execution-identity fingerprint derived from normalized semantic anchors; occurrence-only values such as `manifest_id` and ledger history are intentionally excluded |
| `schema_version`        | `str`      |      yes | Control-plane schema version                                                                                                                                                  |
| `created_at`            | `datetime` |      yes | Manifest creation timestamp                                                                                                                                                   |
| `run_id`                | `uuid`     |      yes | Execution run identifier                                                                                                                                                      |
| `run_type`              | `str`      |      yes | `incremental`, `backfill`, `rebuild`                                                                                                                                          |
| `pipeline_name`         | `str`      |      yes | Canonical pipeline ID                                                                                                                                                         |
| `provider`              | `str`      |      yes | Source provider                                                                                                                                                               |
| `entity`                | `str`      |      yes | Domain entity                                                                                                                                                                 |
| `launch_context`        | `object`   |      yes | Launch options relevant to execution                                                                                                                                          |
| `runtime_config`        | `object`   |      yes | Runtime-only settings snapshot                                                                                                                                                |
| `resolved_config`       | `object`   |      yes | Effective resolved pipeline config                                                                                                                                            |
| `code_provenance`       | `object`   |      yes | See the full `RunCodeProvenance` field set below                                                                                                                              |
| `replay_capability`     | `str`      |      yes | Replay classification: `exact_replay_supported`, `resume_only`, or `rebuild_only`                                                                                             |
| `replay_of_run_id`      | `str`      |       no | Parent run anchor when this manifest is an exact replay of a prior run                                                                                                        |
| `replay_of_manifest_id` | `str`      |       no | Parent manifest anchor when this manifest is an exact replay of a prior manifest                                                                                              |
| `source_refs`           | `array`    |       no | Canonical input/source references                                                                                                                                             |
| `planned_artifacts`     | `array`    |       no | Intended output locations by layer                                                                                                                                            |

`launch_context` is also the persisted support-boundary surface for exact replay:

- `execution_context` distinguishes ordinary source execution from composite execution;
- `exact_replay_support_boundary` publishes the strict replay boundary for that execution context:
  - `snapshot_backed_source_runs_only` for ordinary source execution;
  - `composite_snapshot_backed_input_envelope` for composite execution when
    every seed, dependency, and enricher input is represented by immutable
    snapshot refs.
- `replay_family_contract.strict_replay_runtime_verdict` is the operator-facing
  preflight verdict for strict replay requests:
  - `allowed_with_snapshot_backed_source_refs` for supported source families;
  - `requires_full_composite_snapshot_envelope` for composite families;
  - `blocked_outside_supported_boundary` for published source families that
    remain rebuild-only.

### Input snapshot identity vs locator

`source_refs[*].input_snapshots[*]` separates portable identity from replay
locator metadata:

- `content_hash` is the SHA256 hash of captured input bytes.
- `snapshot_id` is content-addressed as `sha256:{content_hash}` and MUST NOT
  include local file paths, mtimes, or other locator-only fields.
- `immutable_uri` is a replay locator. Local cached-Bronze files use portable
  `bronze://{relative_path_from_bronze_root}` URIs instead of absolute checkout
  paths.
- Object storage anchors (`storage_provider`, `object_bucket`, `object_key`,
  `object_version_id`, `etag`, and `last_modified`) are supplemental locator
  anchors. They do not replace `snapshot_id` as semantic identity.
- `captured_at`, `last_modified`, `etag`, and `query_fingerprint` are
  occurrence or lookup metadata; changing them must not change `snapshot_id`
  when the captured bytes are unchanged.

### Effective-config provenance baseline

When `code_provenance.effective_config_artifact_id` is present, the current
published effective-config baseline is:

- canonical YAML-backed `source_refs` persist stable `source_hash` values when
  the referenced config files exist;
- the semantic effective-config artifact lives at
  `effective_config/{artifact_id}.json` and contains the stable
  `semantic_artifact` payload only;
- occurrence-only fields such as `created_at`, resolved-config timestamp, and
  effective-execution timestamp live in
  `effective_config/_occurrences/{run_id}.json` and are not part of the
  semantic effective-config identity;
- file-backed effective-config persistence is fail-closed for semantic
  rewrites: identical semantic payloads are idempotent and leave the existing
  artifact bytes untouched, while conflicting payloads for the same
  `artifact_id` are rejected;
- file-backed effective-config persistence is crash-safe across semantic
  artifact, occurrence envelope, and `run_id -> artifact_id` index writes:
  runtime must not leave a newly committed semantic artifact or occurrence
  envelope behind when a later consistency step fails in-process.

### `RunCodeProvenance` field set

`code_provenance` currently includes these optional anchors:

- `pipeline_version`
- `git_commit`
- `source_revision_state`
- `dependency_lock_hash`
- `config_hash`
- `resolved_config_hash`
- `effective_config_hash`
- `contract_ref`
- `contract_version`
- `contract_schema_hash`
- `dq_policy_ref`
- `rule_bundle_version`
- `dq_contract_compatibility_hash`
- `effective_config_artifact_id`

Hash semantics are deliberately split:

- `config_hash` is a legacy compatibility anchor retained for older manifest
  and sidecar consumers. Current write paths populate it from
  `resolved_config_hash`; new code must read the explicit
  `resolved_config_hash` / `effective_config_hash` fields and must not treat
  `config_hash` as a synonym for `effective_config_hash`.
- `resolved_config_hash` is the hash of the resolved declarative configuration
  before occurrence envelope fields and supported runtime overrides are folded
  into the execution surface.
- `effective_config_hash` is the hash of the final effective execution
  configuration after supported runtime overrides and control-plane
  normalization.

New manifest creation, diagnostics, inspection output, metadata sidecars, and
lineage nodes MUST preserve those fields separately. Backward-compatible
consumers MAY still read legacy `config_hash`, but manifest hydration and new
control-plane write paths MUST NOT synthesize missing `resolved_config_hash` or
`effective_config_hash` values from it.

Strict exact-replay, `replay_ready`, and `forensic_grade` manifests require
`git_commit` to be present. Inspection diagnostics must expose both
`git_commit` and `source_revision_state` through `diagnostics`,
`code_provenance_state`, and `identity_graph` so missing or dirty code
provenance is visible to operators and automation. New manifests should record
`dependency_lock_hash` as a forensic anchor when a repository lockfile is
available; the field is not a domain I/O concern and must be resolved by
composition/runtime wiring. Diagnostics expose `dependency_lock_state` as
`present` or `missing` so absent lockfile evidence remains operator-visible.
Metadata sidecars and checkpoint metadata carry the same lock hash when it is
available through the run context.

Checkpoint / resume compatibility may additionally rely on a narrower
runtime-anchor contract derived from a subset of control-plane fields such as
`manifest_id`, `composite_run_identity`, `effective_config_hash`,
`contract_ref`, `contract_version`, and `effective_config_artifact_id`. That
runtime-anchor contract is intentionally not the same thing as the canonical
`execution_fingerprint`: `composite_run_identity` is occurrence-scoped resume
identity, not semantic manifest identity.

## Run Ledger Contract

`RunLedgerEntry` is append-only and records what actually happened.

| Field                 | Type       | Required | Notes                                                                                                                                |
| --------------------- | ---------- | -------: | ------------------------------------------------------------------------------------------------------------------------------------ |
| `entry_id`            | `str`      |      yes | Stable ledger-entry ID                                                                                                               |
| `manifest_id`         | `str`      |      yes | Foreign key to manifest                                                                                                              |
| `run_id`              | `uuid`     |      yes | Execution run identifier                                                                                                             |
| `event_type`          | `str`      |      yes | Lifecycle / diagnostic event name                                                                                                    |
| `occurred_at`         | `datetime` |      yes | Event timestamp                                                                                                                      |
| `event_family`        | `str`      |       no | Stable event taxonomy (`diagnostic`, `pipeline.lifecycle`, `pipeline.phase`, `artifact`, `dq`, `lineage`, `checkpoint`, `composite`) |
| `status`              | `str`      |       no | Outcome/status snapshot                                                                                                              |
| `stage`               | `str`      |       no | Stage identifier when applicable                                                                                                     |
| `message`             | `str`      |       no | Human-readable event note                                                                                                            |
| `error_type`          | `str`      |       no | Error class/category for failures                                                                                                    |
| `dataset_ref`         | `str`      |       no | Dataset identity anchor for published artifacts                                                                                      |
| `lineage_fragment_id` | `str`      |       no | Lineage fragment identity anchor                                                                                                     |
| `metrics_snapshot`    | `object`   |       no | Numeric metrics captured at event time                                                                                               |
| `details`             | `object`   |       no | Additional structured payload                                                                                                        |

### `details._diagnostic` anchor contract

When `details` is present, runtime enriches it with `_diagnostic` metadata. The
anchor payload includes:

- stable envelope: `diagnostic_contract_version`, `event_type`, `event_family`,
  `manifest_id`, `run_id`, `status`;
- runtime correlation anchors when available: `pipeline`, `provider`, `entity`,
  `run_type`, `effective_config_hash`, `contract_ref`, `contract_version`,
  `dq_policy_ref`, `rule_bundle_version`, `dq_contract_compatibility_hash`,
  `effective_config_artifact_id`, `composite_run_id`;
- event-specific linkage: `stage`, `dataset_ref`, `lineage_fragment_id`,
  `error_type`.

## Current Event Set / Inspection Baseline

The current baseline ledger records these events:

- `manifest_created`
- `run_started`
- `stage_started`
- `stage_completed`
- `artifact_published`
- `run_finished`
- `run_failed`
- `run_shutdown`
- `dq_policy_applied`

Event taxonomy behavior:

- `event_type` is normalized to lowercase.
- `event_family` is auto-inferred when omitted.
- Prefix-based families are supported (`dq_*`, `lineage_*`, `checkpoint_*`,
  `composite_*`, `artifact_*`), and suffix-based phase events
  (`*_started`, `*_completed`) map to `pipeline.phase`.
- file-backed ledger reads are corruption-visible and fail closed: a truncated
  tail line or malformed JSONL entry is treated as ledger corruption rather
  than silently ignored during inspection or resume-time replay.

## Manifest Diff Classification

`run-manifest diff` should classify differences between two manifests using the
current control-plane reproducibility model:

- `identical`: no top-level manifest differences are present;
- `occurrence_only`: only occurrence-scoped fields such as `manifest_id`,
  `run_id`, or `created_at` differ while `execution_fingerprint` is unchanged;
- `semantic_drift`: manifests differ in semantic execution identity and
  therefore are not exact semantic replays of the same computation;
- `semantic_equivalent_with_noncanonical_differences`: manifests share the same
  `execution_fingerprint`, but still differ in non-occurrence serialized fields
  and should be investigated as normalization or contract drift.

The diff payload should therefore expose:

- `classification`
- `semantic_equivalent`
- `occurrence_only`
- `occurrence_difference_fields`
- `semantic_difference_fields`
- `noncanonical_difference_fields`
- `replay_relationship`
- `forensic_diff` / `cross_surface_replay_diff`, retaining the legacy
  `cross_surface_replay_diff` key for CLI/API compatibility while exposing a
  unified forensic view of manifest, effective-config, checkpoint-anchor,
  lineage, input-snapshot, and planned-artifact drift.

The application-level `ForensicRunDiffService` builds the same report through
the existing manifest and ledger ports. It must classify missing optional
evidence, such as absent run-ledger entries or missing published artifacts,
rather than silently treating unavailable evidence as a match.
The operator-facing CLI/API entrypoints are:

- `bioetl run-manifest forensic-diff <LEFT> <RIGHT>`
- `bioetl diagnostics forensic-diff <LEFT> <RIGHT>`

The `forensic-diff` report is a bounded application DTO with explicit sections
for `replay_capability`, `checkpoint_compatibility`, `artifact_completeness`,
`lineage_closure`, and `missing_evidence`. Missing sidecars, incomplete
produced-artifact traces, absent ledger entries, and unsupported lineage
closure are represented as missing/unsupported evidence instead of being
collapsed into a successful match.

## Canonical Stage Sets

When `event_type` is `stage_started` or `stage_completed`, the current contract
freezes these canonical stage names:

- ordinary runner stages:
  - `preflight`
  - `prepare_medallion_layers`
  - `execute_pipeline`
  - `postrun`
  - `checkpoint_finalize`
- composite runner stages:
  - `seed`
  - `dependencies`
  - `enrichment`
  - `merge`

These stage sets are intentionally stable contract surface. Stage events are
canonicalized to lowercase pipeline stage names, while non-stage events may use
non-pipeline vocabulary such as artifact layer names in `stage`.

## Invariants

1. When the control-plane contract is enabled, `no manifest, no run` applies to the documented execution path.
1. Manifest creation happens before execution starts.
1. `RunManifest` is immutable after persistence.
1. `RunLedgerEntry` is append-only.
1. Sidecars and runtime diagnostics reference `manifest_id` instead of embedding the full manifest payload.
1. `run_id` lookup resolves to one `manifest_id` through the file index.
1. Composite resume reuses checkpoint snapshot data and only replays ledger
   events after the persisted watermark.

## CLI Inspection

Supported inspection commands:

```bash
bioetl run-manifest show <run-id|manifest-id>
bioetl run-manifest diff <left> <right>
bioetl run-manifest score <run-id|manifest-id>
```

The CLI resolves `manifest_id` directly and falls back to `run_id` lookup when
an identifier parses as UUID-like input. Default output is human-readable
`text`; use `--format json` or `--format yaml` for machine-readable output.

`show` returns a four-part inspection payload:

- `manifest`
- `ledger_entries`
- `diagnostics`
- `identity_graph`

The `diagnostics` block is built from
`src/bioetl/application/services/control_plane/run_manifest_diagnostics.py` and is the
published operator-facing summary for event counts, artifact linkage, DQ
anchors, correlation-anchor gaps, replay capability, and suggested next steps.
Diagnostics also include `append_mode_semantic_sinks`; any enabled Silver/Gold
semantic sink with `mode=append` is reported as
`append_mode_semantic_outputs` in `exact_replay_blockers` and as a
`reproducible_semantic_output_mode` persistence gap.

`score` emits the `reproducibility_audit_score` block directly for automation.
The score payload includes `schema_version`, `contract_version`, `scale`,
`required_profile`, run-scoped `score_scope`, backward-compatible
run-scoped `overall_score`, category scores, score `thresholds`,
`threshold_failures`, `thresholds_satisfied`, `blockers`, `evidence_refs`,
explicit `supported_boundary_verdict`, explicit `global_reproducibility_claim`,
`scored_at`, and `source`.

`overall_score` remains a legacy-compatible summary for the inspected
run/family within its published replay boundary. It is not a project-wide claim
that BioETL supports universal exact replay for every family and every
historical occurrence.

`supported_boundary_verdict` is the machine-readable run verdict. It answers
whether the inspected run satisfies its published boundary requirements or is
blocked/gapped by replay capability, lineage closure, thresholds, or other
boundary evidence.

`global_reproducibility_claim` is the machine-readable project-wide claim
surface. It remains explicit even when the inspected run scores well inside its
supported boundary. Until the published contract changes, the platform does not
claim universal exact reproducibility outside the supported boundary.

Current published lineage closure boundary for Bronze -> Silver -> Gold
operator-grade trace/debug support covers these source families:

- `chembl.activity`
- `chembl.molecule`
- `crossref.publication`
- `pubchem.compound`
- `pubmed.publication`

For each supported family the canonical semantic artifact anchors remain:

- Bronze batch outputs emitted for the family source path;
- Silver dataset outputs with canonical artifact ids of the form
  `silver:{family}@<version>`;
- Gold dataset outputs with canonical artifact ids of the form
  `gold:{family}`.

Families outside that published list may still emit lineage signals, but they
are fail-closed outside the supported end-to-end closure surface for
operator-grade trace/debug guarantees.
The diagnostics payload therefore publishes an explicit
`lineage_closure_boundary` contract for every manifested run. When
`lineage_closure_boundary.supported=false`, the run must not be treated as
forensic-grade even if replay-ready and ledger/linkage anchors are otherwise
present.

For the supported MVP surface, sidecar/lineage bundles MUST satisfy this
minimal identity contract:

- `runtime.run_id` matches the lineage fragment `run_id`;
- `runtime.manifest_id` matches the lineage fragment `manifest_id` when both
  are present;
- `output.artifact_id` matches the produced artifact node exposed by the
  lineage fragment;
- `output.lineage_fragment_id` matches the published lineage fragment id.
- inspection diagnostics expose `artifact_refs[*].artifact_id` as the
  operator-facing alias of the published `dataset_ref` so sidecar, ledger, and
  inspection surfaces can be correlated without translation.

The lineage fragment anchor itself is intentionally split:

- `output.lineage_fragment_id` and ledger `lineage_fragment_id` remain the
  semantic fragment identity used by sidecars, manifests, and artifact-linkage
  diagnostics;
- persisted lineage storage may additionally expose an occurrence-scoped
  `stored_fragment_id` to distinguish multiple historical fragment payloads
  that share one semantic `fragment_id`;
- when more than one stored occurrence exists for the same semantic fragment,
  operator tooling must treat direct lookup by semantic `fragment_id` as
  ambiguous and resolve history through `run_id` or `manifest_id` instead of
  silently returning an arbitrary occurrence record.

Bundle assembly MUST fail closed on mismatched preexisting sidecar anchors
instead of silently overwriting them with lineage-derived values.

Replay intent and replay proof are intentionally distinct in this inspection
surface:

- `requested_exact_replay` reports launch-time operator intent from
  `launch_context.exact_replay`;
- `exact_replay_support_boundary` reports whether the manifested execution
  context can ever be strict-replayable. Current published values are
  `snapshot_backed_source_runs_only` and
  `composite_snapshot_backed_input_envelope`;
- `replay_family_contract` publishes the per-family replay contract that
  decides whether strict exact replay is supported for this manifested family;
- `replay_capability` and `exact_replay_eligible` report what the persisted
  immutable input snapshot set actually proves about the run;
- `exact_replay_blockers` explains why a run is not exact-replay eligible;
- `replay_mode=exact_replay` is only emitted when exact replay was requested
  and the manifest carries immutable input snapshots;
- snapshot-backed runs that captured immutable inputs without being launched as
  exact replay are rendered as `replay_mode=same_data_state_recovery`;
- non-snapshot source runs that stay outside strict exact replay are rendered
  as `replay_mode=rebuild`.
- `replay_of_run_id` and `replay_of_manifest_id` record replay ancestry when a
  run is an explicit exact replay of a previous execution rather than merely a
  semantically equivalent new run;
- for the published `bioetl run` surface, these ancestry anchors are only
  accepted together with `--exact-replay`; ordinary rerun/rebuild execution
  must not publish replay parentage;
- `run-manifest diff` reports this ancestry separately through
  `replay_relationship` so replay parentage is visible without collapsing it
  into occurrence-only or semantic drift classifications.

Composite execution can publish `exact_replay_supported` only when the manifest
captures a full immutable snapshot envelope for every seed, dependency, and
enricher pipeline. Composite manifests without that full envelope remain
`rebuild_only`, and `replay_ready` / `forensic_grade` composite launches fail
closed before execution.

For replay-safe runs the published inspection surface MUST expose compact replay
anchors derived from manifest source refs:

- `requested_exact_replay`
- `exact_replay_anchors`
- `input_snapshot_ids`
- `input_snapshot_content_hashes`
- `input_snapshot_identity_fingerprint`
- `produced_artifact_trace`

These fields are derived operator-facing summaries used to line up run-manifest
inspection with checkpoint compatibility diagnostics; they do not expand the
persisted `RunManifest` storage schema.

`exact_replay_anchors` is the semantic replay section. It intentionally excludes
occurrence-only identifiers such as `manifest_id` and `run_id`; those values stay
in the surrounding inspection payload and occurrence diagnostics.
Runtime `BatchID`, quarantine `entry_id`, and domain-event `event_id` values are
also occurrence-scoped correlation/idempotency identifiers. UUID4 generation for
those values is allowed only when inventoried in
`configs/quality/determinism_identity_policy.yaml`, and those identifiers must
not enter `execution_fingerprint` or persisted dataset content hashes.

`produced_artifact_trace` is rooted at the manifest lookup key and is resolved
from run-ledger artifact publication events only. A run cannot claim
`replay_ready` unless this trace is complete, because replay inspection must be
able to move from `manifest_id` to concrete produced artifacts without scraping
logs or metadata sidecars.

The paired effective-config artifact publishes a separate semantic provenance
table through `semantic_artifact.source_class_provenance`. That table makes the
supported source classes explicit:

- `config_file`
- `cli_override`
- `env_override`
- `runtime_adjustment`
- `dq_policy_contract`
- `immutable_input_snapshot` as an external anchor on the run manifest
- `implicit_process_environment` as intentionally unsupported ambient state

`execution_fingerprint` in this contract now means the canonical
execution-identity fingerprint shared across manifest persistence, checkpoint
metadata, and runtime compatibility checks. It is derived from normalized
semantic execution anchors and intentionally excludes occurrence-only values
such as `manifest_id`, ledger entry order, and diagnostic summaries.

Dataset-level metadata-sidecar identity is also semantic-only:

- sidecar `output.content_hash` must exclude occurrence-scoped runtime anchors
  such as `run_id`, `manifest_id`, `composite_run_id`, and write/lineage
  timestamps even if they appear in one intermediate row payload;
- changing occurrence-only runtime drift must not change replay eligibility,
  replay mode, or manifest diff classification.

## References

- [CLI Reference](../cli.md)
- [Run Manifest Inspection Runbook](../../05-operations/runbooks/run-manifest-inspection.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../../00-project/00-map.md)
