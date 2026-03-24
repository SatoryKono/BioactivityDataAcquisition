# Run Manifest Inspection

*Last verified: 2026-03-24*

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

Operationally:

- when `run_manifest_enabled=false`, no control-plane artifact is expected;
- when `run_manifest_enabled=true` and `run_ledger_enabled=false`, manifest
  inspection still works but ledger history is intentionally absent.

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

## Storage Locations

When direct filesystem inspection is needed:

```text
data/output/control/run_manifest/{manifest_id}.json
data/output/control/run_manifest/_by_run_id/{run_id}.txt
data/output/control/run_ledger/{manifest_id}.jsonl
data/output/control/run_ledger/_by_run_id/{run_id}.txt
```

## Escalation Guidance

Escalate if:

- `run_id` has no manifest index entry;
- ledger exists but is empty;
- `run_finished` is missing for a run reported as successful;
- sidecar metadata lacks `manifest_id`.

See also:

- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest & Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
