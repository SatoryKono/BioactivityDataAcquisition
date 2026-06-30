______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Domain Invariants

## Purpose

This page collects the current high-signal invariants that span aggregates,
workflow orchestration, control-plane ownership, and domain/schema boundaries.

## Aggregate Invariants

See [Aggregate State Machines](aggregate-state-machines.md) for the formal
transition tables behind these summaries.

| Surface | Invariants |
| --- | --- |
| `Batch` | Records may be added or quarantined only while `OPEN`; write flow cannot skip `SEALED`; terminal write result is `COMMITTED` or `FAILED`. |
| `PipelineRun` | Runs start from `PENDING`; terminal states block further transitions; success requires stage evidence; failure/shutdown stay explicit. |
| `QuarantineEntry` | Entry identity and payload evidence are mandatory; resolution transitions are explicit; reprocessing requires replacement identity evidence. |

## Replay-Critical Value Object Invariants

| Surface | Invariants |
| --- | --- |
| `RunContext` | `started_at` must be timezone-aware; `pipeline_name`, `provider`, and `entity` cannot be empty; replay/provenance anchors such as `execution_fingerprint`, `required_persistence_profile`, `replay_of_run_id`, `replay_of_manifest_id`, and `input_snapshot_fingerprint` stay explicit fields on the immutable context rather than being inferred from wall-clock state. |
| `StageResult` | `stage` cannot be empty; `records_processed` cannot be negative; `FAILED` requires `error`; `SUCCESS` and `FAILED` require `completed_at`. |

## Workflow DAG Invariants

Current source of truth: `src/bioetl/domain/workflow/dag.py`

- each workflow must define at least one step;
- `step_id` values must be unique;
- every dependency must reference a declared step;
- the dependency graph must be acyclic;
- execution order is derived topologically, not by YAML file order alone.

## Workflow Control-Plane Invariants

Current source of truth:

- `src/bioetl/domain/control_plane/`
- `src/bioetl/domain/ports/control_plane/`
- ADR-044, ADR-046, ADR-047

Canonical rules:

- `WorkflowManifest` is immutable intent and must not be reused as mutable
  status.
- `WorkflowLedger` is append-only history and operator-intent evidence, not the
  sole mutable resume owner.
- `WorkflowExecutionState` is the mutable owner for current status, error
  projection, repair state, and ambiguity markers.
- Destructive replay or recovery must not be inferred silently when ambiguity is
  present; explicit operator intent is required.

## Schema-Boundary Invariants

ADR-048 ratifies the current boundary:

- Pandera/Pandas are allowed in domain only as schema-contract representation
  inside the sanctioned schema/contract surfaces.
- Domain runtime behavior must not become framework-owned I/O logic.
- Contract and schema pages must point back to live domain contract code, not
  introduce a second semantic authority.

## Port and Adapter Invariants

- Ports remain pure contracts and must not acquire concrete adapter behavior.
- `bioetl.domain.ports` is the sanctioned first-party import facade.
- Optional observability or memory features may use NoOp ports, but the contract
  surface must remain stable.

## Related References

- [Aggregates](aggregates.md)
- [Aggregate State Machines](aggregate-state-machines.md)
- [Ports](ports.md)
- [Workflow State Machine](workflow-state-machine.md)
- [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-047](../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- [ADR-048](../../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md)
