______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Domain Aggregates

## Purpose

This page catalogs the current aggregate roots in `src/bioetl/domain/aggregates/`
and their enforced lifecycle boundaries.

## Aggregate Catalog

| Aggregate | Public root | Child objects | Core invariants | Lifecycle / state machine | Primary source files |
| --- | --- | --- | --- | --- | --- |
| `Batch` | `Batch` | `BatchRecord`, `BatchStatus` | `start_index >= 0`; records may be added or quarantined only while `OPEN`; write flow cannot skip sealing | `OPEN -> SEALED -> WRITING -> COMMITTED/FAILED` | `batch.py`, `_batch_aggregate.py`, `_batch_lifecycle.py` |
| `PipelineRun` | `PipelineRun` | `StageResult`, `PipelineRunState`, `StageStatus` | run may start only from `PENDING`; terminal states block further transitions; successful completion requires stage evidence | `PENDING -> RUNNING -> COMPLETED/FAILED/SHUTDOWN` | `pipeline_run.py`, `_pipeline_run_mixins.py`, `pipeline_run_stage_result.py`, `pipeline_run_state.py` |
| `QuarantineEntry` | `QuarantineEntry` | `ResolutionInfo`, `QuarantineStatus` | `entry_id`, `pipeline_name`, `error_code`, `payload`, and `payload_hash` are mandatory; reprocessing requires replacement identity | `NEW -> UNDER_REVIEW -> IGNORED/REPROCESSED`, plus `NEW/UNDER_REVIEW -> EXPIRED` | `quarantine_entry.py`, `_quarantine_aggregate.py`, `_quarantine_entry_transitions_mixin.py` |

## Aggregate Responsibilities

### Batch

- Owns batch assembly before durable storage writes.
- Tracks valid/quarantined counts before commit.
- Emits aggregate coordination events such as `BatchCreated`, `BatchSealed`,
  `BatchWritten`, and `BatchFailed`.

### PipelineRun

- Owns one pipeline execution lifecycle at domain level.
- Tracks per-stage outcomes through immutable `StageResult` value objects.
- Protects terminal lifecycle semantics independently from application service
  orchestration.

### QuarantineEntry

- Owns the lifecycle of one quarantined record or payload.
- Preserves triage state, resolution details, and reprocessing outcomes.
- Separates operational review transitions from storage/reporting adapters.

## State-Machine Anchors

| Aggregate | State owner file | Notes |
| --- | --- | --- |
| `Batch` | `src/bioetl/domain/aggregates/_batch_lifecycle.py` | Write lifecycle only; storage adapters execute outside the aggregate. |
| `PipelineRun` | `src/bioetl/domain/aggregates/_pipeline_run_mixins.py` | Stage evidence is part of the aggregate model, not only logging. |
| `QuarantineEntry` | `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py` | Resolution transitions remain explicit and auditable. |

## Related References

- [Invariants](invariants.md)
- [Events](events.md)
- [Workflow State Machine](workflow-state-machine.md)
- [ADR-021 DDD Aggregates](../../02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md)
