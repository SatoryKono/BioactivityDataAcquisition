# Run Manifest Inspection

*Last verified: 2026-03-25*

## Purpose

Use this runbook when you need to answer:

- what exact config/provenance a run used;
- whether two runs are reproducibly equivalent;
- whether lifecycle events were emitted for a run;
- whether sidecars can be traced back to one control-plane record.

This runbook assumes the supported Local-Only runtime profile and the
file-backed control-plane MVP introduced by ADR-044.

## Feature Flags

The control-plane layer is governed by runtime settings under
`settings.pipeline.control_plane`:

- `run_manifest_enabled`
- `run_ledger_enabled`
- `checkpoint_compatibility_policy` (`observe|soft_fail|hard_fail`)

Operationally:

- when `run_manifest_enabled=false`, no control-plane artifact is expected;
- when `run_manifest_enabled=true` and `run_ledger_enabled=false`, manifest
  inspection still works but ledger history is intentionally absent.
- when resume is enabled, `checkpoint_compatibility_policy` controls behavior on
  checkpoint/runtime identity mismatch (`observe` logs-only, `soft_fail` blocks
  resume, `hard_fail` raises error).

## Inputs

You need one of:

- `run_id`
- `manifest_id`

## Quick Commands

### Show one run

```bash
bioetl run-manifest show <run-id|manifest-id>
```

The default output is a compact human-readable `text` view. Use
`--format json` or `--format yaml` when a machine-readable payload is needed.

### Fast diagnostics extraction

```bash
bioetl run-manifest show <run-id|manifest-id> --format json
```

Use the `diagnostics` block for immediate triage:

- `latest_status`, `latest_event_type` - current execution outcome;
- `event_family_counts`, `event_type_counts` - event-stream health summary;
- `artifact_refs` - direct links from run to published dataset artifacts;
- `lineage_fragment_ids` - lineage fragment linkage visibility;
- `missing_artifact_links` - count of artifact events without
  `dataset_ref/lineage_fragment_id`.
- `alert_signals` - normalized boolean incident signals for routing/escalation.
- `next_steps` - operator-oriented next actions derived from active signals.

### Diff two runs

```bash
bioetl run-manifest diff <left> <right>
```

The default output is a compact human-readable `text` diff. Use
`--format json` or `--format yaml` when piping or storing the result.

Use this for replay/debug questions such as:

- same pipeline but different resolved config;
- same run type but different code provenance;
- same inputs but different planned artifact targets.

## What To Check

### 1. Confirm manifest identity

Verify:

- `manifest_id`
- `run_id`
- `pipeline_name`
- `run_type`

If a `run_id` cannot be resolved to a manifest, treat this as a control-plane
integrity issue.

### 2. Confirm code provenance

Review:

- `pipeline_version`
- `git_commit`
- `config_hash`

If two runs should be equivalent but one of these fields differs, the runs are
not reproducibly identical.

### 3. Confirm effective config

Inspect:

- `code_provenance.effective_config_artifact_id`
- `code_provenance.config_hash`
- `runtime_config`
- `resolved_config`
- `source_refs`
- `planned_artifacts`

This is the fastest way to determine whether a CLI override, source query, or
artifact target changed between runs.

### 4. Confirm ledger lifecycle

For a healthy successful run with ledger enabled, expect at least:

- `manifest_created`
- `run_started`
- one or more `stage_completed`
- zero or more `artifact_published`
- `run_finished`

For interrupted or failing runs, expect `run_failed` and/or `run_shutdown`.

### 5. Confirm diagnostics linkage quality

Inspect:

- `diagnostics.total_events`
- `diagnostics.event_family_counts`
- `diagnostics.artifact_refs`
- `diagnostics.lineage_fragment_ids`
- `diagnostics.missing_artifact_links`

Escalate when:

- `missing_artifact_links > 0` for production-critical runs;
- `artifact_published` exists but `artifact_refs` is empty;
- `lineage_fragment_ids` is unexpectedly empty for Silver/Gold publishing runs.

## Storage Locations

When direct filesystem inspection is needed:

```text
data/output/control/run_manifest/{manifest_id}.json
data/output/control/run_manifest/_by_run_id/{run_id}.txt
data/output/control/run_ledger/{manifest_id}.jsonl
data/output/control/run_ledger/_by_run_id/{run_id}.txt
data/output/control/effective_config/{artifact_id}.json
data/output/control/effective_config/_by_run_id/{run_id}.txt
```

## Runtime Diagnostic Events

When effective-config persistence is healthy, logs include:

- `effective_config_artifact_persisted`

When persistence/linkage fails before runner assembly completes, logs include:

- `effective_config_artifact_persist_failed`

Use these events together with `run_id` and `manifest_id` to accelerate
triage of control-plane regressions.

## CI Gate

Track D regression checks run in the dedicated CI job:

- GitHub Actions workflow `Tests` -> job `track-d-gates`

This gate verifies fixture-governance invariants, checkpoint compatibility
policy behavior, and tracked-fixture control-plane linkage.

## Escalation Guidance

Escalate if:

- `run_id` has no manifest index entry;
- ledger exists but is empty;
- `run_finished` is missing for a run reported as successful;
- sidecar metadata lacks `manifest_id`.
- `diagnostics.missing_artifact_links > 0` and incident severity is P0/P1;
- `event_family_counts` is inconsistent with expected lifecycle for run status
  (for example, `latest_status=success` without `pipeline.lifecycle` completion).

See also:

- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest & Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
