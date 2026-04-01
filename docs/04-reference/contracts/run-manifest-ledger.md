---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-01'
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
- `src/bioetl/interfaces/cli/commands/run_manifest.py`
- `src/bioetl/composition/bootstrap/cli/run_manifest.py`
- `src/bioetl/composition/runtime_builders/run_manifest_builder.py`
- `src/bioetl/composition/runtime_builders/runner_builder.py`
- `src/bioetl/composition/factories/pipeline/checkpoint_policy_helpers.py`
- `src/bioetl/infrastructure/config/_base.py`
- `src/bioetl/infrastructure/control_plane/`

## Storage Layout

File-backed control-plane persistence uses the following canonical paths:

| Artifact | Path |
|---|---|
| Manifest payload | `data/output/control/run_manifest/{manifest_id}.json` |
| Manifest run-id index | `data/output/control/run_manifest/_by_run_id/{run_id}.txt` |
| Ledger payload | `data/output/control/run_ledger/{manifest_id}.jsonl` |
| Ledger run-id index | `data/output/control/run_ledger/_by_run_id/{run_id}.txt` |

`run_manifest` and `run_ledger` stores are bootstrapped from
`Path(settings.data_dir) / "output" / "control" / <leaf>` and are therefore
runtime-aligned with the current composition layer.

## Rollout Flags

The control-plane runtime is governed by the runtime object path
`settings.pipeline.control_plane`. The source-of-truth model is
`PipelineSettings.ControlPlaneSettings` in
`src/bioetl/infrastructure/config/_base.py`.

| Setting | Default | Effect |
|---|---:|---|
| `run_manifest_enabled` | `true` | Create immutable manifest before runner assembly / execution starts |
| `run_ledger_enabled` | `true` | Append lifecycle and inspection events keyed by `manifest_id` |
| `checkpoint_compatibility_policy` | `soft_fail` | Resume behavior when checkpoint identity mismatches runtime (`observe`, `soft_fail`, `hard_fail`) |

Current rollout semantics:

1. `run_manifest_enabled=false` disables both manifest creation and ledger attachment for new runs because runtime assembly coerces the effective flag set to `(False, False)`.
2. `run_manifest_enabled=true`, `run_ledger_enabled=false` keeps manifest creation but suppresses ledger writes.
3. `run_ledger_enabled=true` is only valid when `run_manifest_enabled=true`.
4. `checkpoint_compatibility_policy` governs resume disposition on checkpoint incompatibility:
   `observe` logs and continues, `soft_fail` blocks resume, `hard_fail` raises an error.

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
| `event_type` | `str` | yes | Lifecycle / diagnostic event name |
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

When `details` is present, runtime enriches it with `_diagnostic` metadata. The
anchor payload includes:

- stable envelope: `contract_version`, `event_type`, `event_family`,
  `manifest_id`, `run_id`, `status`;
- runtime correlation anchors when available: `pipeline`, `provider`, `entity`,
  `run_type`, `effective_config_hash`, `contract_ref`, `data_contract_version`,
  `dq_policy_ref`, `rule_bundle_version`, `dq_contract_compatibility_hash`,
  `effective_config_artifact_id`, `composite_run_id`;
- event-specific linkage: `stage`, `dataset_ref`, `lineage_fragment_id`,
  `error_type`.

## Current Event Set / Inspection Baseline

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

1. When the control-plane contract is enabled, `no manifest, no run` applies to the documented execution path.
2. Manifest creation happens before execution starts.
3. `RunManifest` is immutable after persistence.
4. `RunLedgerEntry` is append-only.
5. Sidecars and runtime diagnostics reference `manifest_id` instead of embedding the full manifest payload.
6. `run_id` lookup resolves to one `manifest_id` through the file index.

## CLI Inspection

Supported inspection commands:

```bash
bioetl run-manifest show <run-id|manifest-id>
bioetl run-manifest diff <left> <right>
```

The CLI resolves `manifest_id` directly and falls back to `run_id` lookup when
an identifier parses as UUID-like input. Default output is human-readable
`text`; use `--format json` or `--format yaml` for machine-readable output.

`show` returns a three-part inspection payload:

- `manifest`
- `ledger_entries`
- `diagnostics`

The `diagnostics` block is built from
`src/bioetl/application/services/run_manifest_diagnostics.py` and is the
published operator-facing summary for event counts, artifact linkage, DQ
anchors, correlation-anchor gaps, alert signals, and suggested next steps.

## References

- [CLI Reference](../cli.md)
- [Run Manifest Inspection Runbook](../../05-operations/runbooks/run-manifest-inspection.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Project Navigator](../../00-project/00-map.md)
