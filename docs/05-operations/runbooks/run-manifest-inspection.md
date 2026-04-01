---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Priority: P1
Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
Last verified: '2026-04-01'
---

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
- `checkpoint_compatibility_policy` with allowed values `observe | soft_fail | hard_fail`

Fast source-of-truth checks:

```bash
rg -n "run_manifest_enabled|run_ledger_enabled|checkpoint_compatibility_policy" \
  src/bioetl/infrastructure/config/_base.py \
  src/bioetl/composition/runtime_builders/runner_builder.py \
  src/bioetl/composition/factories/pipeline/checkpoint_policy_helpers.py \
  src/bioetl/application/core/lifecycle/checkpoint_runtime.py
```

Interpretation:

- if `run_manifest_enabled=false`, no new control-plane artifact is expected for new runs;
- if `run_manifest_enabled=true` and `run_ledger_enabled=false`, manifest inspection still works but ledger history is intentionally absent;
- if `run_manifest_enabled=false`, runtime assembly also coerces ledger attachment off for new runs;
- if resume is enabled, `checkpoint_compatibility_policy` controls checkpoint identity mismatch handling.

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

Focus on:

- `latest_status`, `latest_event_type`, `total_events`;
- `event_family_counts`, `event_type_counts`;
- `artifact_refs`, `lineage_fragment_ids`, `missing_artifact_links`;
- `dq_rule_ids`, `dq_dispositions`, `dq_report_paths`, `dq_violation_kinds`;
- `cross_validation_rule_ids`, `cross_validation_config_paths`, `cross_validation_signal_present`;
- `effective_config_hash`, `contract_ref`, `contract_version`, `dq_policy_ref`, `rule_bundle_version`, `effective_config_artifact_id`, `dq_contract_compatibility_hash`;
- `correlation_anchor_gaps`, `alert_signals`, `next_steps`.

Interpretation examples:

- `latest_status=success` with no `run_finished` is suspicious;
- `artifact_published` with empty `artifact_refs` indicates traceability degradation;
- `missing_artifact_links > 0` means artifact events are missing `dataset_ref` and/or `lineage_fragment_id` anchors;
- `correlation_anchor_gaps.effective_config_hash > 0` means execution-critical ledger events lost effective config linkage;
- `correlation_anchor_gaps.data_contract_version > 0` on failure-critical runs means contract traceability is incomplete.

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve the inspected identifiers, commands, decisive evidence, and follow-up actions in incident notes.

## Verification

- Manifest resolution works by `run_id` or `manifest_id`.
- The returned manifest contains stable provenance anchors such as `config_hash`, `contract_ref`, `contract_version`, and `effective_config_artifact_id` when available.
- Ledger history matches the observed run outcome and event baseline.
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
