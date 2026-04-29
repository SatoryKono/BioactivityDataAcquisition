______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-23'

______________________________________________________________________

# Run Manifest Inspection

## Trigger

- Use this runbook when operators must inspect run provenance, lifecycle history, or control-plane integrity for a pipeline run.
- Use it when a `run_id` must be mapped to one immutable manifest and one append-only ledger stream.
- This is the published operator runbook for the supported `run-manifest`
  inspection surface and the runbook leg of the D-01 traceability
  documentation pack.

## Impact

- Priority: P1.
- Delayed handling increases incident triage time and can hide provenance, artifact-linkage, or resume-compatibility defects.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant control-plane artifacts.
- Relevant runtime settings are materialized on `settings.pipeline.control_plane`;
  the source-of-truth model is `src/bioetl/infrastructure/config/_base.py`.

## Procedure

### 1. Confirm rollout flags

Verify the active rollout semantics:

- `run_manifest_enabled`
- `run_ledger_enabled`
- `required_persistence_profile` with allowed values
  `degraded_observable | replay_ready | forensic_grade`
- `checkpoint_compatibility_policy` with allowed values `observe | soft_fail | hard_fail | legacy_observe`

Fast source-of-truth checks:

```bash
rg -n "run_manifest_enabled|run_ledger_enabled|required_persistence_profile|checkpoint_compatibility_policy" \
  src/bioetl/infrastructure/config/_base.py \
  src/bioetl/composition/runtime_builders/runner_builder.py \
  src/bioetl/composition/factories/pipeline/checkpoint_policy_helpers.py \
  src/bioetl/application/core/lifecycle/checkpoint_runtime.py
```

Interpretation:

- if `run_manifest_enabled=false`, no new control-plane artifact is expected for new runs;
- if `run_manifest_enabled=true` and `run_ledger_enabled=false`, manifest inspection still works but ledger history is intentionally absent;
- if `run_manifest_enabled=false`, runtime assembly also coerces ledger attachment off for new runs;
- if `required_persistence_profile=replay_ready`, runtime bootstrap requires
  `run_manifest_enabled=true` and an execution context inside the strict
  exact-replay support boundary;
- if `required_persistence_profile=forensic_grade`, runtime bootstrap requires
  both `run_manifest_enabled=true` and `run_ledger_enabled=true`, plus
  metadata-sidecar / lineage persistence on every active published sink layer;
- if resume is enabled, `checkpoint_compatibility_policy` controls checkpoint mismatch handling:
  `observe` may continue only for degraded non-identity signals, while canonical
  execution-identity mismatches still block resume.
- if `checkpoint_compatibility_policy=legacy_observe`, treat it as a temporary
  migration-only degraded mode: it may still surface legacy validation signals,
  but identity continuity must already be proven or resume remains blocked.
- if `required_persistence_profile` is `replay_ready` or `forensic_grade`,
  runtime does not allow `observe` / `legacy_observe` to remain effective; the
  applied policy is coerced to at least `soft_fail`.
- if the current run is `exact_replay=true`, runtime coerces checkpoint
  compatibility handling to `hard_fail`; exact replay is not allowed to
  continue after any compatibility mismatch.

### 2. Resolve one run

Show one manifest by `run_id` or `manifest_id`:

```bash
bioetl run-manifest show <run-id|manifest-id>
```

For machine-readable triage output:

```bash
bioetl run-manifest show <run-id|manifest-id> --format json
```

Interpretation:

- successful resolution returns `manifest`, optional `ledger_entries`, and `diagnostics`;
- if a UUID-like identifier resolves by `manifest_id`, that payload is returned directly;
- otherwise the CLI falls back to `run_id -> manifest_id` resolution through the sidecar index.
- text mode renders the payload as `Manifest`, `Code Provenance`, `Execution Inputs`, `Ledger`, and `Diagnostics`.

### 3. Compare two runs

Compare two manifests resolved by `run_id` or `manifest_id`:

```bash
bioetl run-manifest diff <left> <right>
bioetl run-manifest diff <left> <right> --format yaml
```

Interpretation:

- differences are computed over top-level manifest fields using canonical JSON comparison;
- differences in `resolved_config`, `runtime_config`, `code_provenance`, `source_refs`, or `planned_artifacts` mean the runs are not reproducibly identical.
- for effective-config provenance, treat `source_refs[*].source_hash` as the
  canonical source-file anchor when present; occurrence timestamps inside the
  effective-config artifact are UTC-normalized and should not by themselves be
  interpreted as semantic drift.
- `execution_fingerprint` is the canonical execution-identity fingerprint shared
  across manifest, checkpoint, and runtime compatibility surfaces.
- this fingerprint intentionally excludes occurrence-only anchors such as
  `manifest_id`, ledger history, and operator-facing diagnostics.
- `composite_run_identity` is a separate occurrence-scoped resume anchor used
  only to prevent composite checkpoint drift; it must not be interpreted as a
  replacement for the semantic `execution_fingerprint`.
- checkpoint compatibility may also use a narrower runtime-anchor contract when a persisted manifest fingerprint is unavailable, but that contract is intentionally smaller and must not be read as a substitute for full manifest identity.

### 4. Inspect storage layout directly when needed

Canonical filesystem paths:

```text
data/output/control/run_manifest/{manifest_id}.json
data/output/control/run_manifest/_by_run_id/{run_id}.txt
data/output/control/run_ledger/{manifest_id}.jsonl
data/output/control/run_ledger/_by_run_id/{run_id}.txt
```

Useful direct checks:

```bash
cat data/output/control/run_manifest/_by_run_id/<run_id>.txt
cat data/output/control/run_manifest/<manifest_id>.json
tail -n 20 data/output/control/run_ledger/<manifest_id>.jsonl
cat data/output/control/run_ledger/_by_run_id/<run_id>.txt
rg -n '"event_type":"(manifest_created|run_started|stage_started|stage_completed|artifact_published|run_finished|run_failed|run_shutdown|dq_policy_applied)"' \
  data/output/control/run_ledger/<manifest_id>.jsonl
rg -n '"_diagnostic"|"effective_config_hash"|"contract_ref"|"dq_policy_ref"|"effective_config_artifact_id"' \
  data/output/control/run_ledger/<manifest_id>.jsonl
```

Interpretation:

- missing manifest sidecar for an enabled control-plane path is an integrity issue;
- missing ledger file is expected only when `run_ledger_enabled=false` or the run never reached ledger attachment;
- run-id index files MUST resolve to one `manifest_id`.
- a run-id index that points at a missing or different manifest is storage
  corruption, not a cache miss; `bioetl run-manifest show` should surface a
  corruption error, and read metrics should emit
  `bioetl_control_plane_reads_total{store="manifest",status="failed"}`.
- `_diagnostic` anchors SHOULD be present on persisted ledger entries once the ledger is attached.

### 5. Validate invariants

Check the enabled-path invariants:

- no manifest, no run;
- manifest created before execution;
- manifest immutable after persistence;
- ledger append-only;
- sidecars and diagnostics reference `manifest_id` instead of embedding manifest.

Operational interpretation:

- `manifest_created` SHOULD be the first control-plane event when ledger is enabled;
- a successful run SHOULD have a manifest even if the ledger is disabled;
- append-only means ledger history grows by new lines and existing entries are not rewritten.

### 5a. Inspect composite resume / replay state when resume behavior matters

The supported resume contract is intentionally dual-mode:

- ordinary resume uses checkpoint snapshot state and compatibility checks
  without ledger suffix replay;
- composite resume uses checkpoint snapshot state as the base and then applies
  ledger suffix replay.

Composite resume currently follows a checkpoint snapshot + ledger suffix replay
model.

Fast source-of-truth checks:

```bash
rg -n "last_event_id|last_event_occurred_at|list_entries_after|project_run_ledger_replay" \
  src/bioetl/application/composite/checkpoint/load_service.py \
  src/bioetl/domain/control_plane/run_ledger.py \
  src/bioetl/domain/ports/control_plane/run_ledger.py
```

Interpretation:

- ordinary runs should not be diagnosed as if they were expected to replay
  ledger suffix state; their supported resume source is the checkpoint snapshot;
- replay is only applied after compatibility anchors are validated;
- replay consumes only ledger entries strictly after `last_event_id`;
- replay is intentionally coarse-grained: it restores lifecycle milestones and
  watermark metadata, not rich checkpoint payloads;
- composite resume additionally enforces `composite_run_identity`; a missing or
  mismatched occurrence anchor is a resume blocker even when other semantic
  anchors match;
- a missing watermark entry for the current manifest indicates checkpoint
  incompatibility and should be treated as a resume blocker on the fail-closed
  path.

### 6. Check current event baseline

For a healthy successful run with ledger enabled, expect the baseline event family to include:

- `manifest_created`
- `run_started`
- one or more `stage_started`
- one or more `stage_completed`
- zero or more `artifact_published`
- `run_finished`

For interrupted or failing runs, inspect for:

- `run_failed`
- `run_shutdown`
- `dq_policy_applied` when DQ enforcement participated in the outcome

### 7. Interpret diagnostics output

The `diagnostics` block from `bioetl run-manifest show --format json` is the
fastest triage surface.

The current published Bronze -> Silver -> Gold lineage closure boundary for
operator-grade trace/debug claims covers these source families:

- `chembl.activity`
- `chembl.molecule`
- `crossref.works`
- `pubchem.compound`
- `pubmed.publication`

Outside that documented family set, lineage signals may still exist but they
remain outside the supported closure boundary for operator-grade trace/debug
claims.
Inspection now exposes that boundary explicitly through
`diagnostics.lineage_closure_boundary`; operators MUST treat
`lineage_closure_boundary.supported=false` as a fail-closed block on
forensic-grade trace/debug claims for that family.

Focus on:

- `latest_status`, `latest_event_type`, `total_events`;
- `event_family_counts`, `event_type_counts`;
- `artifact_refs`, `lineage_fragment_ids`, `missing_artifact_links`;
- `required_persistence_profile`;
- `lineage_closure_boundary.family`,
  `lineage_closure_boundary.supported`,
  `lineage_closure_boundary.reason`;
- `replay_family_contract.family`,
  `replay_family_contract.contract`,
  `replay_family_contract.strict_exact_replay_supported`,
  `replay_family_contract.reason`;
- `persistence_profile.attained_profile`, `persistence_profile.required_profile`,
  `persistence_profile.required_profile_satisfied`,
  `persistence_profile.surfaces`,
  `persistence_profile.required_profile_missing_requirements`,
  `persistence_profile.replay_ready_missing_requirements`,
  `persistence_profile.forensic_grade_missing_requirements`;
- `dq_rule_ids`, `dq_dispositions`, `dq_report_paths`, `dq_violation_kinds`;
- `cross_validation_rule_ids`, `cross_validation_config_paths`, `cross_validation_signal_present`;
- `execution_fingerprint` as the canonical execution-identity fingerprint shared
  across manifest, checkpoint, and runtime compatibility surfaces;
- `config_hash`, `resolved_config_hash`, and `effective_config_hash` as
  separate config provenance fields; `config_hash` is a legacy compatibility
  anchor, `resolved_config_hash` identifies the resolved declarative config,
  and `effective_config_hash` identifies the final effective execution config;
- `effective_config_hash`, `contract_ref`, `contract_version`, and `effective_config_artifact_id` as runtime-anchor compatibility fields;
- stable `source_refs[*].source_hash` values in the effective-config artifact
  when canonical config files are available;
- `current_identity` and `checkpoint_identity` when resume compatibility was
  rejected or degraded; these compact payloads surface
  `composite_run_identity`, `execution_fingerprint`, `manifest_id`,
  `effective_config_hash`, `contract_ref`, `contract_version`, `exact_replay`,
  `input_snapshot_ids`, and `input_snapshot_content_hashes`;
- `dq_policy_ref`, `rule_bundle_version`, and `dq_contract_compatibility_hash` as adjacent DQ/control-plane anchors that are related but not interchangeable with manifest identity;
- `correlation_anchor_gaps`, `alert_signals`, `next_steps`.

Interpretation examples:

- `latest_status=success` with no `run_finished` is suspicious;
- `artifact_published` with empty `artifact_refs` indicates traceability degradation;
- `missing_artifact_links > 0` means artifact events are missing `dataset_ref` and/or `lineage_fragment_id` anchors;
- if `resolved_config_hash` and `effective_config_hash` differ, treat that as
  expected evidence that runtime overrides or control-plane normalization
  changed the final execution surface; do not collapse either value into
  legacy `config_hash`;

### 7a. Supported trace/debug path from output artifact to run context

For the published supported lineage closure surface, the canonical operator path is:

1. Start from the output sidecar (`*_metadata.yaml`) and read:
   - `runtime.run_id`
   - `runtime.manifest_id`
   - `output.artifact_id`
   - `output.lineage_fragment_id`
1. Resolve the immutable run context:
   - `bioetl run-manifest show <run_id|manifest_id> --format json`
1. Inspect:
   - `diagnostics.artifact_refs`
   - `diagnostics.lineage_fragment_ids`
   - `identity_graph.execution_fingerprint`
   - `manifest.source_refs`
   - `ledger_entries` for `artifact_published`
1. Treat `diagnostics.artifact_refs[*].artifact_id` as the operator-facing alias
   of the published `dataset_ref` so that sidecar `output.artifact_id`,
   inspection diagnostics, and ledger linkage all use the same visible anchor.
1. Confirm that:
   - the sidecar `artifact_id` matches the produced artifact referenced by the
     lineage fragment;
   - the sidecar `lineage_fragment_id` matches one of the published fragment
     anchors for the run;
   - `run_id` and `manifest_id` line up across sidecar, manifest, and ledger.

For historical lineage reconstruction, distinguish two fragment identities:

- `lineage_fragment_id` is the semantic fragment anchor shared by sidecars,
  ledger diagnostics, and manifest inspection;
- `stored_fragment_id` is the occurrence-scoped persisted lineage record id
  exposed by lineage inspection when more than one historical fragment payload
  shares the same semantic `lineage_fragment_id`.

If one semantic fragment id resolves to multiple stored occurrences, treat
direct lookup by semantic `lineage_fragment_id` as ambiguous and pivot through
`run_id` / `manifest_id` instead of accepting the first matching fragment.

If any of those anchors disagree, treat it as lineage integrity drift rather
than silently accepting the bundle as canonical.

- `persistence_profile.attained_profile=forensic_grade` means the run is both
  replay-ready and backed by ledger/artifact-lineage evidence suitable for
  stronger postmortem reconstruction within the current supported lineage
  closure boundary;
- `persistence_profile.attained_profile=replay_ready` means exact replay anchors
  and a concrete produced-artifact trace are present, but richer forensic
  surfaces are still incomplete;
- `persistence_profile.attained_profile=degraded_observable` means manifest
  inspection still works, but replay-ready requirements are missing and should
  be read from `*_missing_requirements`;
- `exact_replay_anchors` is the semantic replay section and intentionally
  excludes occurrence-only identifiers such as `manifest_id` and `run_id`;
- `produced_artifact_trace` is resolved from run-ledger artifact publication
  events by `manifest_id`; if it is incomplete, do not treat the run as
  replay-ready even when manifest snapshots and exact replay capability are
  present;
- `exact_replay_support_boundary=snapshot_backed_source_runs_only` means only
  snapshot-backed source runs can become strict-replayable in the current
  model;
- `replay_family_contract.strict_exact_replay_supported=true` means the current
  family is inside the published strict exact-replay contract; `false` is a
  fail-closed signal even if immutable input snapshots exist;
- `exact_replay_support_boundary=composite_snapshot_backed_input_envelope`
  means composite exact replay requires immutable snapshot refs for every seed,
  dependency, and enricher input before the run can be treated as
  exact-replayable;
- `replay_of_run_id`, `replay_of_manifest_id`, and `replay_parentage` identify
  explicit exact-replay ancestry and distinguish it from a merely semantically
  equivalent fresh run;
- on the published `bioetl run` surface these ancestry anchors are only valid
  when the run was launched with `--exact-replay`; if the operator sees them on
  an ordinary rerun/rebuild path, treat that as control-plane drift;
- `run-manifest diff` exposes that ancestry through `replay_relationship`
  without collapsing it into occurrence-only drift;
- `replay_mode=same_data_state_recovery` means the run captured immutable
  snapshots and can recreate the same data state, but it was not launched as an
  explicit exact replay of a prior run;
- `replay_mode=rebuild` means the run is on the ordinary rebuild/rerun path and
  operators must not read it as strict exact replay or snapshot-backed same-data-state
  recovery;
- `alert_signals.immutable_input_snapshot_gap=true` means the run is still on
  the ordinary source boundary, but immutable cached-Bronze input snapshots are
  missing, so strict exact replay cannot be claimed yet;
- `alert_signals.composite_resume_reconstructability_gap=true` means the run is
  on the bounded composite resume path: expect checkpoint snapshot +
  ledger-suffix reconstruction only, not full rich checkpoint-state recovery;
- `alert_signals.required_persistence_profile_gap=true` means the run did not
  meet the minimum persistence profile declared at launch time and must not be
  treated as satisfying that operator contract;
- one-run dossier `status.operational_success=false` means runtime success and
  dossier evidence did not jointly satisfy the active operator contract;
- for critical runs where `required_profile=forensic_grade`,
  `status.operational_success_criteria.dossier_evidence_satisfied` must be
  `true` before the run is marked operationally successful;
- `degraded_evidence` containing `critical_dossier_evidence_gap` means the run
  may have completed, but missing/degraded dossier evidence still blocks
  operational success for the critical profile;
- `alert_signals.produced_artifact_trace_gap=true` means the inspection surface
  could not resolve concrete produced artifacts from the manifest's run ledger;
- `alert_signals.replay_ready_gap=true` means the run must not be treated as
  exact-replay ready even if manifest inspection itself is available;
- `alert_signals.forensic_grade_gap=true` means the run must not be treated as
  full postmortem/trace reconstruction evidence without checking the listed
  missing requirements;
- `alert_signals.lineage_closure_boundary_gap=true` means the current pipeline
  family is outside the published operator-grade lineage closure boundary and
  must not be presented as forensic-grade even if other replay/ledger anchors
  are present;
- `correlation_anchor_gaps.effective_config_hash > 0` means execution-critical ledger events lost effective config linkage;
- `correlation_anchor_gaps.contract_version > 0` on failure-critical runs means contract traceability is incomplete.
- `persistence_profile.composite_resume_reconstructability` states the current
  composite replay boundary explicitly with
  `scope=coarse_grained_composite_resume`: lifecycle milestones and watermarks
  are reconstructed from persisted state, but rich checkpoint payloads are not.

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve the inspected identifiers, commands, decisive evidence, and follow-up actions in incident notes.

## Verification

- Manifest resolution works by `run_id` or `manifest_id`.
- The returned manifest exposes `config_hash`, `resolved_config_hash`, and
  `effective_config_hash` separately when available; only older hydrated
  manifests may show compatibility values copied from legacy `config_hash`.
- The returned manifest contains stable provenance anchors such as `contract_ref`, `contract_version`, and `effective_config_artifact_id` when available.
- Ledger history matches the observed run outcome and event baseline.
- For composite resume, checkpoint watermark metadata and replayed ledger suffix
  align with the latest observed lifecycle state.
- Diagnostics interpretation is captured with evidence in incident notes or follow-up tasks.

## Rollback

- This runbook is inspection-only; no rollback is required for read-only diagnostics.
- If mitigation or recovery commands are executed after inspection, revert config overrides or temporary local state before leaving the incident.

## Post-incident

- Record the inspected identifiers (`run_id`, `manifest_id`), commands executed, and the decisive evidence.
- Open follow-up work when event baseline, anchors, or storage layout deviate from the control-plane contract.

## References

- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
- [CLI Reference](../../04-reference/cli.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../../00-project/00-map.md)
