---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
  - BioETL Team
Last verified: "2026-04-02"
---

# Run Manifest and Run Ledger Contract

## Purpose

This document defines the published control-plane contract for immutable run
manifests, append-only run ledgers, and the inspection surface used by
operators and diagnostics.

It is the contract leg of the published traceability documentation pack
required by [D-01](../../00-project/governance/01-documentation-governance-style-guide.md).

The current code owners / source-of-truth seams are:

- `src/bioetl/domain/control_plane/run_manifest.py`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/domain/ports/control_plane/`
- `src/bioetl/application/services/run_manifest_service.py`
- `src/bioetl/application/services/run_ledger_service.py`
- `src/bioetl/application/services/run_manifest_diagnostics.py`
- `src/bioetl/application/services/run_manifest_inspection_service.py`
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

| Artifact              | Path                                                       |
| --------------------- | ---------------------------------------------------------- |
| Manifest payload      | `data/output/control/run_manifest/{manifest_id}.json`      |
| Manifest run-id index | `data/output/control/run_manifest/_by_run_id/{run_id}.txt` |
| Ledger payload        | `data/output/control/run_ledger/{manifest_id}.jsonl`       |
| Ledger run-id index   | `data/output/control/run_ledger/_by_run_id/{run_id}.txt`   |

`run_manifest` and `run_ledger` stores are bootstrapped from
`Path(settings.data_dir) / "output" / "control" / <leaf>` and are therefore
runtime-aligned with the current composition layer.

## Rollout Flags

The control-plane runtime is governed by the runtime object path
`settings.pipeline.control_plane`. The source-of-truth model is
`PipelineSettings.ControlPlaneSettings` in
`src/bioetl/infrastructure/config/_base.py`.

| Setting                           |     Default | Effect                                                                                            |
| --------------------------------- | ----------: | ------------------------------------------------------------------------------------------------- |
| `required_persistence_profile`    | `degraded_observable` | Minimum control-plane persistence contract required for this runtime (`degraded_observable`, `replay_ready`, `forensic_grade`) |
| `run_manifest_enabled`            |      `true` | Create immutable manifest before runner assembly / execution starts                               |
| `run_ledger_enabled`              |      `true` | Append lifecycle and inspection events keyed by `manifest_id`                                     |
| `checkpoint_compatibility_policy` | `soft_fail` | Resume behavior when checkpoint identity mismatches runtime (`observe`, `soft_fail`, `hard_fail`) |

Current rollout semantics:

1. `run_manifest_enabled=false` disables both manifest creation and ledger attachment for new runs because runtime assembly coerces the effective flag set to `(False, False)`.
1. `run_manifest_enabled=true`, `run_ledger_enabled=false` keeps manifest creation but suppresses ledger writes.
1. `run_ledger_enabled=true` is only valid when `run_manifest_enabled=true`.
1. `required_persistence_profile=replay_ready` requires `run_manifest_enabled=true`.
1. `required_persistence_profile=forensic_grade` requires both `run_manifest_enabled=true` and `run_ledger_enabled=true`.
1. `checkpoint_compatibility_policy` governs resume disposition on checkpoint incompatibility:
   `observe` remains a degraded operator mode for non-identity signals, but canonical
   execution-identity mismatches still block resume; `soft_fail` blocks resume;
   `hard_fail` raises an error.

## Supported Resume Modes

The current control-plane contract intentionally supports two different resume
modes:

- ordinary resume uses checkpoint snapshot state and compatibility checks
  without ledger suffix replay;
- composite resume uses checkpoint snapshot state as the base and then replays
  only the ledger suffix strictly after `last_event_id`.

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
  outputs;
- `replay_ready`: immutable input snapshots, exact-replay capability, and the
  effective-config artifact anchor are present, but richer forensic surfaces may
  still be absent;
- `degraded_observable`: the run remains inspectable through the persisted
  manifest, but one or more mandatory replay-ready requirements are missing.

The current diagnostics surface exposes:

- `persistence_profile.attained_profile`;
- `persistence_profile.claims`;
- `persistence_profile.surfaces`;
- `persistence_profile.replay_ready_missing_requirements`;
- `persistence_profile.forensic_grade_missing_requirements`.
- `alert_signals.immutable_input_snapshot_gap`;
- `alert_signals.composite_resume_reconstructability_gap`;
- `alert_signals.replay_ready_gap`;
- `alert_signals.forensic_grade_gap`;

When ledger-backed diagnostics are available, these profile gaps are promoted
into alert-oriented booleans and operator next steps so replay/forensic
deficiencies are visible as actionable signals rather than passive metadata.
When immutable input snapshots are the missing replay-ready requirement, the
diagnostics surface raises `alert_signals.immutable_input_snapshot_gap` and
points the operator back to cached-Bronze snapshot persistence before exact
replay can be claimed.

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

| Field                   | Type       | Required | Notes                                            |
| ----------------------- | ---------- | -------: | ------------------------------------------------ |
| `manifest_id`           | `str`      |      yes | Stable identifier of the manifest record         |
| `execution_fingerprint` | `str`      |      yes | Canonical execution-identity fingerprint derived from normalized semantic anchors; occurrence-only values such as `manifest_id` and ledger history are intentionally excluded |
| `schema_version`        | `str`      |      yes | Control-plane schema version                     |
| `created_at`            | `datetime` |      yes | Manifest creation timestamp                      |
| `run_id`                | `uuid`     |      yes | Execution run identifier                         |
| `run_type`              | `str`      |      yes | `incremental`, `backfill`, `rebuild`             |
| `pipeline_name`         | `str`      |      yes | Canonical pipeline ID                            |
| `provider`              | `str`      |      yes | Source provider                                  |
| `entity`                | `str`      |      yes | Domain entity                                    |
| `launch_context`        | `object`   |      yes | Launch options relevant to execution             |
| `runtime_config`        | `object`   |      yes | Runtime-only settings snapshot                   |
| `resolved_config`       | `object`   |      yes | Effective resolved pipeline config               |
| `code_provenance`       | `object`   |      yes | See the full `RunCodeProvenance` field set below |
| `replay_capability`     | `str`      |      yes | Replay classification: `exact_replay_supported`, `resume_only`, or `rebuild_only` |
| `source_refs`           | `array`    |       no | Canonical input/source references                |
| `planned_artifacts`     | `array`    |       no | Intended output locations by layer               |

`launch_context` is also the persisted support-boundary surface for exact replay:

- `execution_context` distinguishes ordinary source execution from composite execution;
- `exact_replay_support_boundary` publishes the strict replay boundary for that execution context:
  - `snapshot_backed_source_runs_only` for ordinary source execution;
  - `composite_execution_unsupported` for composite execution.

### `RunCodeProvenance` field set

`code_provenance` currently includes these optional anchors:

- `pipeline_version`
- `git_commit`
- `config_hash`
- `contract_ref`
- `contract_version`
- `contract_schema_hash`
- `dq_policy_ref`
- `rule_bundle_version`
- `dq_contract_compatibility_hash`
- `effective_config_artifact_id`

Checkpoint / resume compatibility may additionally rely on a narrower
runtime-anchor contract derived from a subset of control-plane fields such as
`manifest_id`, `effective_config_hash`, `contract_ref`, `contract_version`, and
`effective_config_artifact_id`. That runtime-anchor contract is intentionally
not the same thing as the canonical `execution_fingerprint`.

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
`src/bioetl/application/services/run_manifest_diagnostics.py` and is the
published operator-facing summary for event counts, artifact linkage, DQ
anchors, correlation-anchor gaps, replay capability, and suggested next steps.

Current supported lineage MVP boundary for Bronze -> Silver -> Gold closure:

- Bronze batch outputs for the representative `chembl.activity` family;
- Silver dataset outputs with canonical artifact ids of the form
  `silver:chembl.activity@<version>`;
- Gold dataset outputs with canonical artifact ids of the form
  `gold:chembl.activity`.

This boundary is intentionally narrow. Other families may emit lineage signals,
but they are not yet the explicitly supported end-to-end closure surface for
operator-grade trace/debug guarantees.

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

Bundle assembly MUST fail closed on mismatched preexisting sidecar anchors
instead of silently overwriting them with lineage-derived values.

Replay intent and replay proof are intentionally distinct in this inspection
surface:

- `requested_exact_replay` reports launch-time operator intent from
  `launch_context.exact_replay`;
- `exact_replay_support_boundary` reports whether the manifested execution
  context can ever be strict-replayable. Current published values are
  `snapshot_backed_source_runs_only` and `composite_execution_unsupported`;
- `replay_capability` and `exact_replay_eligible` report what the persisted
  immutable input snapshot set actually proves about the run;
- `exact_replay_blockers` explains why a run is not exact-replay eligible;
- `replay_mode=exact_replay` is only emitted when exact replay was requested
  and the manifest carries immutable input snapshots;
- snapshot-backed runs that captured immutable inputs without being launched as
  exact replay are rendered as `replay_mode=snapshot_backed_run`.

Composite execution is currently outside the strict exact-replay support
boundary. Composite manifests therefore publish
`exact_replay_support_boundary=composite_execution_unsupported` and remain
`rebuild_only` even when they consume cached Bronze inputs.

For replay-safe runs the published inspection surface MUST expose compact replay
anchors derived from manifest source refs:

- `requested_exact_replay`
- `input_snapshot_ids`
- `input_snapshot_content_hashes`
- `input_snapshot_identity_fingerprint`

These fields are derived operator-facing summaries used to line up run-manifest
inspection with checkpoint compatibility diagnostics; they do not expand the
persisted `RunManifest` storage schema.

`execution_fingerprint` in this contract now means the canonical
execution-identity fingerprint shared across manifest persistence, checkpoint
metadata, and runtime compatibility checks. It is derived from normalized
semantic execution anchors and intentionally excludes occurrence-only values
such as `manifest_id`, ledger entry order, and diagnostic summaries.

## References

- [CLI Reference](../cli.md)
- [Run Manifest Inspection Runbook](../../05-operations/runbooks/run-manifest-inspection.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../../00-project/00-map.md)
