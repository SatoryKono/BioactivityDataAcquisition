______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-30'

______________________________________________________________________

# Aggregate State Machines

## Purpose

This page is the canonical published reference for the formal lifecycle
transitions of the current aggregate roots in `src/bioetl/domain/aggregates/`.

Use it when you need transition-level semantics rather than the higher-level
catalog in [Aggregates](aggregates.md).

## Sources Of Truth

- `src/bioetl/domain/aggregates/_batch_lifecycle.py`
- `src/bioetl/domain/aggregates/_batch_status.py`
- `src/bioetl/domain/aggregates/_pipeline_run_mixins.py`
- `src/bioetl/domain/aggregates/pipeline_run_state.py`
- `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py`
- `src/bioetl/domain/aggregates/_quarantine_value_objects.py`

## `Batch`

### States

- `OPEN`
- `SEALED`
- `WRITING`
- `COMMITTED`
- `FAILED`

### Allowed transitions

| From | Operation | To | Source |
| --- | --- | --- | --- |
| `OPEN` | create batch | `OPEN` | `emit_batch_created(...)` records creation evidence without changing the initial state |
| `OPEN` | `seal(...)` | `SEALED` | `_batch_lifecycle.seal` |
| `SEALED` | `mark_writing(...)` | `WRITING` | `_batch_lifecycle.mark_writing` |
| `WRITING` | `mark_committed(...)` | `COMMITTED` | `_batch_lifecycle.mark_committed` |
| `WRITING` | `mark_failed(...)` | `FAILED` | `_batch_lifecycle.mark_failed` |

### Guard conditions

- `seal(...)` is allowed only while `status.is_modifiable()`, which currently
  means `OPEN`.
- `mark_writing(...)` rejects any state except `SEALED`.
- `mark_committed(...)` and `mark_failed(...)` reject any state except
  `WRITING`.
- `COMMITTED` and `FAILED` are terminal for the write lifecycle.

### Domain events

- `BatchCreated`
- `BatchSealed`
- `BatchWritten`
- `BatchFailed`
- `RecordQuarantined`

## `PipelineRun`

### States

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `SHUTDOWN`

### Allowed transitions

| From | Operation | To | Source |
| --- | --- | --- | --- |
| `PENDING` | `start(...)` | `RUNNING` | `_pipeline_run_mixins.start` |
| `RUNNING` | `record_stage_failure(...)` | `FAILED` | `_pipeline_run_mixins.record_stage_failure` |
| `RUNNING` | `complete(...)` | `COMPLETED` | `_pipeline_run_mixins.complete` |
| `RUNNING` | `fail(...)` | `FAILED` | `_pipeline_run_mixins.fail` |
| `RUNNING` | `shutdown(...)` | `SHUTDOWN` | `_pipeline_run_mixins.shutdown` |

Stage-level evidence is also recorded while the aggregate remains `RUNNING`:

- `record_stage_start(...)` appends a `StageResult` with `StageStatus.RUNNING`
- `record_stage_success(...)` appends a `StageResult` with `StageStatus.SUCCESS`
- `record_stage_failure(...)` appends a `StageResult` with `StageStatus.FAILED`
  and moves the aggregate to terminal `FAILED`

### Guard conditions

- `start(...)` is allowed only from `PENDING`.
- All mutation methods except `start(...)` require aggregate state `RUNNING`.
- `complete(...)` additionally requires:
  - no failed stages;
  - at least one recorded stage;
  - every recorded stage in `StageStatus.SUCCESS`.
- `COMPLETED`, `FAILED`, and `SHUTDOWN` are terminal by
  `PipelineRunState.is_terminal()`.

### Domain events

- `PipelineCompleted`
- `PipelineFailed`
- `PipelineShutdown`

## `QuarantineEntry`

### States

- `NEW`
- `UNDER_REVIEW`
- `IGNORED`
- `REPROCESSED`
- `EXPIRED`

### Allowed transitions

| From | Operation | To | Source |
| --- | --- | --- | --- |
| `NEW` | `start_review()` | `UNDER_REVIEW` | `_quarantine_entry_transitions_mixin.start_review` |
| `NEW` | `mark_ignored(...)` | `IGNORED` | `_quarantine_entry_transitions_mixin.mark_ignored` |
| `UNDER_REVIEW` | `mark_ignored(...)` | `IGNORED` | `_quarantine_entry_transitions_mixin.mark_ignored` |
| `NEW` | `mark_reprocessed(...)` | `REPROCESSED` | `_quarantine_entry_transitions_mixin.mark_reprocessed` |
| `UNDER_REVIEW` | `mark_reprocessed(...)` | `REPROCESSED` | `_quarantine_entry_transitions_mixin.mark_reprocessed` |
| `NEW` | `mark_expired(...)` | `EXPIRED` | `_quarantine_entry_transitions_mixin.mark_expired` |
| `UNDER_REVIEW` | `mark_expired(...)` | `EXPIRED` | `_quarantine_entry_transitions_mixin.mark_expired` |

### Guard conditions

- `start_review()` is allowed only from `NEW`.
- `mark_ignored(...)` and `mark_reprocessed(...)` require
  `QuarantineStatus.can_resolve()`, which currently allows only `NEW` and
  `UNDER_REVIEW`.
- `mark_reprocessed(...)` additionally requires a non-empty `new_record_id`.
- `mark_expired(...)` rejects any terminal state.
- `add_metadata(...)` is allowed only while the entry is unresolved; terminal
  statuses reject metadata changes.
- `IGNORED`, `REPROCESSED`, and `EXPIRED` are terminal by
  `QuarantineStatus.is_terminal()`.

### Domain events and resolution evidence

- `mark_ignored(...)` records `ResolutionInfo(resolution_type="ignored", ...)`
  and emits `QuarantineEntryResolved`.
- `mark_reprocessed(...)` records
  `ResolutionInfo(resolution_type="reprocessed", new_record_id=..., ...)` and
  emits `QuarantineEntryResolved`.
- `mark_expired(...)` records
  `ResolutionInfo(resolution_type="expired", reason="Retention period exceeded")`
  and does not emit a dedicated resolution event in the current code.

## Related References

- [Aggregates](aggregates.md)
- [Invariants](invariants.md)
- [Events](events.md)
- [Workflow State Machine](workflow-state-machine.md)
