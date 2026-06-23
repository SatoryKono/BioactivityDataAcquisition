______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Domain Events

## Purpose

BioETL currently uses two domain-level event surfaces with different roles:

1. immutable aggregate coordination events under
   `src/bioetl/domain/aggregates/events.py`;
2. standardized observability/logging event constants under
   `src/bioetl/domain/events.py`.

These surfaces are related but not interchangeable.

## Aggregate Coordination Events

Aggregate coordination events are immutable past-tense records collected by
aggregates and published by the application layer after successful persistence.

| Event family | Published events | Source |
| --- | --- | --- |
| Pipeline lifecycle | `PipelineCompleted`, `PipelineFailed`, `PipelineShutdown` | `src/bioetl/domain/aggregates/events.py` |
| Batch lifecycle | `BatchCreated`, `BatchSealed`, `BatchWritten`, `BatchFailed` | `src/bioetl/domain/aggregates/events.py` |
| Quarantine lifecycle | `RecordQuarantined`, `QuarantineEntryCreated`, `QuarantineEntryResolved` | `src/bioetl/domain/aggregates/events.py` |

Shared base type:

- `DomainEvent` is frozen and slot-based.
- `event_id` is deterministically derived from event contents when not supplied.
- Event payloads include correlation anchors such as `run_id`, `batch_id`,
  payload hashes, stage names, and error metadata.

## Observability Event Constants

`src/bioetl/domain/events.py` defines standardized event names for structured
logging and metric-friendly observability surfaces.

Key families:

- pipeline lifecycle: `pipeline_started`, `pipeline_finished`,
  `pipeline_failed`, `pipeline_shutdown`;
- batch lifecycle: `batch_started`, `batch_completed`;
- phase events: `*_started`, `*_completed` helpers for ordinary pipeline stages;
- health checks: `health_check_completed`,
  `health_check_summary_recorded`;
- DQ and maintenance: `dq_anomaly_detected`, `vacuum_completed`,
  `artifact_published`.

These constants are for consistent event naming across logs and emitters. They
are not the same thing as persisted aggregate domain events.

## Boundary Rule

- Use aggregate events when the domain model needs immutable lifecycle evidence
  for downstream reactions or persistence-safe publication.
- Use `PipelineEvent` constants when adapters or services need stable structured
  event names for logs, metrics, and tracing.
- Do not treat workflow manifest/ledger records as replacements for aggregate
  domain events; those are separate control-plane artifacts.

## Related References

- [Aggregates](aggregates.md)
- [Workflow State Machine](workflow-state-machine.md)
- [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
