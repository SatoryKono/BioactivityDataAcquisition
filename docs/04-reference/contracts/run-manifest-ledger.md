# Run Manifest and Run Ledger Contract

*Last verified: 2026-03-26*

## Purpose

This document defines the published control-plane contract for immutable run
manifests and append-only run ledgers.

The current code owners are:

- `src/bioetl/domain/control_plane/run_manifest.py`
- `src/bioetl/domain/control_plane/run_ledger.py`
- `src/bioetl/domain/ports/control_plane/`

## Storage Layout

File-backed MVP persistence uses the following paths:

| Artifact | Path |
|---|---|
| Manifest payload | `data/output/control/run_manifest/{manifest_id}.json` |
| Manifest run-id index | `data/output/control/run_manifest/_by_run_id/{run_id}.txt` |
| Ledger payload | `data/output/control/run_ledger/{manifest_id}.jsonl` |
| Ledger run-id index | `data/output/control/run_ledger/_by_run_id/{run_id}.txt` |

## Rollout Flags

The control-plane MVP is governed by two runtime settings under
`settings.pipeline.control_plane`:

| Setting | Default | Effect |
|---|---:|---|
| `run_manifest_enabled` | `true` | Create immutable manifest before runner bootstrap |
| `run_ledger_enabled` | `true` | Append lifecycle and lineage ledger events keyed by `manifest_id` |
| `checkpoint_compatibility_policy` | `soft_fail` | Behavior of `--resume` when checkpoint identity mismatches current runtime (`observe`, `soft_fail`, `hard_fail`) |

Current rollout semantics:

1. `run_manifest_enabled=false` disables both manifest and ledger creation.
2. `run_manifest_enabled=true`, `run_ledger_enabled=false` keeps manifest creation but suppresses ledger writes.
3. `run_ledger_enabled=true` is only valid when `run_manifest_enabled=true`.
4. `checkpoint_compatibility_policy` governs resume disposition on checkpoint incompatibility:
   `observe` (warn+continue), `soft_fail` (block resume), `hard_fail` (raise error).

## Run Manifest Contract

`RunManifest` is immutable and captures launch-time intent plus reproducibility
provenance.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `manifest_id` | `str` | yes | Stable identifier of the manifest record |
| `execution_fingerprint` | `str` | yes | Digest of reproducibility-significant fields |
| `schema_version` | `str` | yes | Control-plane schema version |
| `created_at` | `datetime` | yes | Manifest creation timestamp |
| `run_id` | `uuid` | yes | Execution run identifier |
| `run_type` | `str` | yes | `incremental`, `backfill`, `rebuild` |
| `pipeline_name` | `str` | yes | Canonical pipeline ID |
| `provider` | `str` | yes | Source provider |
| `entity` | `str` | yes | Domain entity |
| `launch_context` | `object` | yes | Launch options relevant to execution |
| `runtime_config` | `object` | yes | Runtime-only settings snapshot |
| `resolved_config` | `object` | yes | Effective resolved pipeline config |
| `code_provenance` | `object` | yes | See the full `RunCodeProvenance` field set below |
| `source_refs` | `array` | no | Canonical input/source references |
| `planned_artifacts` | `array` | no | Intended output locations by layer |

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

## Run Ledger Contract

`RunLedgerEntry` is append-only and records what actually happened.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `entry_id` | `str` | yes | Stable ledger-entry ID |
| `manifest_id` | `str` | yes | Foreign key to manifest |
| `run_id` | `uuid` | yes | Execution run identifier |
| `event_type` | `str` | yes | Lifecycle event name |
| `occurred_at` | `datetime` | yes | Event timestamp |
| `event_family` | `str` | no | Stable event taxonomy (`diagnostic`, `pipeline.lifecycle`, `pipeline.phase`, `artifact`, `dq`, `lineage`, `checkpoint`, `composite`) |
| `status` | `str` | no | Outcome/status snapshot |
| `stage` | `str` | no | Stage identifier when applicable |
| `message` | `str` | no | Human-readable event note |
| `error_type` | `str` | no | Error class/category for failures |
| `dataset_ref` | `str` | no | Dataset identity anchor for published artifacts |
| `lineage_fragment_id` | `str` | no | Lineage fragment identity anchor |
| `metrics_snapshot` | `object` | no | Numeric metrics captured at event time |
| `details` | `object` | no | Additional structured payload |

### `details._diagnostic` anchor contract

When `details` is present, runtime enriches it with `_diagnostic` metadata.
The anchor payload includes:

- Stable envelope: `contract_version`, `event_type`, `event_family`,
  `manifest_id`, `run_id`, `status`.
- Runtime correlation anchors (when available): `pipeline`, `provider`, `entity`,
  `run_type`, `effective_config_hash`, `contract_ref`, `data_contract_version`,
  `dq_policy_ref`, `rule_bundle_version`, `dq_contract_compatibility_hash`,
  `effective_config_artifact_id`, `composite_run_id`.
- Event-specific linkage: `stage`, `dataset_ref`, `lineage_fragment_id`,
  `error_type`.

## Current Event Set

The current baseline ledger records these events:

- `manifest_created`
- `run_started`
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

## Invariants

1. `RunManifest` is created before pipeline execution starts.
2. `RunManifest` is immutable after persistence.
3. `RunLedgerEntry` is append-only.
4. Sidecar/runtime metadata must reference `manifest_id`, not embed full
   manifest payload.
5. `run_id` lookup must resolve to exactly one `manifest_id` via the file index.

## CLI Inspection

Supported inspection commands:

```bash
bioetl run-manifest show <run-id|manifest-id>
bioetl run-manifest diff <left> <right>
```

The CLI defaults to human-readable `text` output; use `--format json` or
`--format yaml` for stable machine-readable serialization.

See also:

- [CLI Reference](../cli.md)
- [Run Manifest Inspection Runbook](../../05-operations/runbooks/run-manifest-inspection.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
