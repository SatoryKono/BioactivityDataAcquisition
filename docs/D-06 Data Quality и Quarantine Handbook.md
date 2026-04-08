---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-08'
---

# D-06: Data Quality and Quarantine Handbook

## Purpose

This handbook describes the current production behavior of Data Quality (DQ) and Quarantine in `main`.
It is an operator-facing reference for triage, replay preparation, and retention cleanup.

## Runtime Profile and Scope

- Runtime profile: Local-Only, single-instance, file-backed control plane.
- Scope: DQ evaluation, quarantine lifecycle, CLI operations, and operational diagnostics.
- Non-goals: no ledger-based resume semantics, no alternate runtime profile design.

## Source of Truth

Use these artifacts as canonical for current behavior:

- DQ config guide: `docs/03-guides/dq-configuration.md`
- Quarantine runbook: `docs/05-operations/runbooks/quarantine-management.md`
- DQ failure runbooks:
  - `docs/05-operations/runbooks/pipeline-failure-dq.md`
  - `docs/05-operations/runbooks/dq-failure-investigation.md`
- CLI implementation:
  - `src/bioetl/interfaces/cli/commands/domains/quarantine/command.py`
  - `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py`
- Quarantine service and storage:
  - `src/bioetl/application/services/quarantine_service.py`
  - `src/bioetl/infrastructure/quarantine/operations.py`
- Status enums:
  - `src/bioetl/domain/types/enums.py`
  - `src/bioetl/domain/aggregates/_quarantine_value_objects.py`

## Current DQ Behavior

- Global threshold defaults:
  - `soft_fail = 0.05`
  - `hard_fail = 0.20`
- `invalid_record_policy` default is `quarantine`.
- Invalid records are routed to `common.quarantine` instead of hard-stopping the whole run by default.
- Silver filter rejects also use `common.quarantine` with:
  - `error_code=FILTERED_OUT_SILVER`
  - `classification=filter_rejection`
  - `quarantine_category=silver_filter`

## Current Quarantine Status Model

### Persisted Delta status (operator-facing)

`QuarantineRecordStatus` in `src/bioetl/domain/types/enums.py`:

- `NEW`
- `IGNORED`
- `REPROCESSED`

These values are used by current CLI actions and table-level operational reporting.

### Domain aggregate lifecycle (broader internal model)

`QuarantineStatus` in `src/bioetl/domain/aggregates/_quarantine_value_objects.py`:

- `new`
- `under_review`
- `ignored`
- `reprocessed`
- `expired`

This lifecycle model is intentionally broader than the persisted Delta status surface.
For current operator flows, persisted statuses remain the actionable source.

## CLI Operations (Current)

Available commands under `bioetl quarantine`:

- `inspect`
- `stats`
- `replay`
- `purge`
- `resolve`

Key behavior:

- `resolve --status` accepts only `IGNORED` or `REPROCESSED`.
- `stats` supports `--run-id`, `--silver-filter-only`, and bounded grouping pivots.
- `inspect` supports `--run-id` and `--silver-filter-only`.

### Replay Semantics

`bioetl quarantine replay` is not a pipeline rerun mechanism.
Current semantics:

1. Select replay candidates (bounded by pipeline, optional error code, and max age).
2. In non-dry-run mode, mark selected records as `REPROCESSED`.
3. Print operator guidance that records are ready for pipeline reprocessing.

The command prepares record state for reprocessing workflows; it does not execute a full pipeline run itself.

## Run-Scoped Silver Filter Triage

Use run-scoped mode when denominator accuracy is required:

- `bioetl quarantine stats --pipeline <pipeline> --silver-filter-only --run-id <run-id>`
- `bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --run-id <run-id> --limit 20`

When `--run-id` is present, CLI stats enrichment can use run-manifest inspection data (control-plane context) for more reliable run-scoped diagnostics.

## Control Plane and Resume Boundary

- Resume execution offset remains checkpoint-based in `main`.
- Run manifest and run ledger are provenance/inspection surfaces and diagnostic context providers.
- Quarantine operations do not convert runtime resume semantics from checkpoint to ledger replay.

## Metrics and Dashboards

For operational monitoring and triage dashboards, use:

- `docs/05-operations/runbooks/quarantine-management.md`
- `docs/03-guides/metrics-monitoring.md`
- `docs/03-guides/dashboards/monitoring-index.md`

These documents define operator dashboard usage (`bioetl-dq-v2`, `bioetl-silver-reject-explorer`, and related views).

## Known Documentation Drift

At the time of verification (`2026-04-08`):

- `docs/04-reference/cli.md` still states quarantine statuses as `NEW, REVIEWED, RESOLVED`.
- Current executable CLI and persisted enum surface are `NEW, IGNORED, REPROCESSED`.

Until the CLI reference entry is corrected, treat command implementation and runbooks listed above as the authoritative source.

## Operator Quick Flow

1. Confirm DQ/quarantine signal spike in Grafana.
2. Use `quarantine stats` with focused grouping (`reason-code`, `field`, `rule-type`, `operator`).
3. Drill down with `quarantine inspect`.
4. Choose disposition:
   - mark known non-actionable records as `IGNORED`;
   - prepare replay candidates and mark as `REPROCESSED`;
   - purge stale records by retention policy.
5. Record actions in incident/runbook notes.

