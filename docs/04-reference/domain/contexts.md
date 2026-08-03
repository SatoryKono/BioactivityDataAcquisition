______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-23'

______________________________________________________________________

# Domain Contexts

## Purpose

This page documents the current domain-level runtime context surfaces used by
BioETL pipeline execution.

Use it when you need the authoritative split between:

- `PipelineRunContext` as the **launch-time** execution descriptor; and
- `PipelineContext` as the **in-run** processing context carried through batch,
  transform, and write paths.

## Source Of Truth

- Facade: `src/bioetl/domain/context.py`
- Launch context owner: `src/bioetl/domain/context_run.py`
- Time helpers: `src/bioetl/domain/context_time.py`
- Validation helpers: `src/bioetl/domain/context_validation.py`
- Correlation helpers: `src/bioetl/domain/context_correlation.py`
- Filtering/cached-Bronze helpers:
  `src/bioetl/domain/context_filtering.py`,
  `src/bioetl/domain/context_cached_bronze.py`

## Exported Context Surface

`bioetl.domain.context` currently exports:

- `PipelineContext`
- `PipelineRunContext`
- `CachedBronzeContext`
- `InputFilterContext`
- `VacuumSettings`
- `MISSING_RUNTIME_TIMESTAMP`

## `PipelineContext`

`PipelineContext` is the runtime object for **in-run** execution paths.

### Fields

| Field | Meaning |
| --- | --- |
| `run_id` | Immutable run identity carried through processing |
| `run_type` | Incremental / backfill / rebuild semantics |
| `logger` | `LoggerPort` abstraction bound to the active run |
| `started_at` | Deterministic timestamp resolved via explicit input or `ClockLike` |
| `source_batch_id` | Optional lineage anchor for the active transform/write path |
| `replay_timestamp_anchor` | Optional replay-sensitive time anchor |
| `pipeline_name` | Optional pipeline identity for shared execution helpers |
| `workflow_id` | Workflow-level linkage; `"standalone"` outside workflow orchestration |

### Behavior

| API | Responsibility |
| --- | --- |
| `PipelineContext.create(...)` | Resolves `started_at` through `resolve_context_started_at()` instead of wall-clock defaults |
| `bind_logger(**kwargs)` | Returns a new `PipelineContext` with additional structured logger bindings |
| `with_source_batch_id(...)` | Returns a new `PipelineContext` with batch-lineage metadata set |

## `PipelineRunContext`

`PipelineRunContext` is the launch/execution descriptor used before the pipeline
enters record-processing flow.

### Field groups

| Group | Representative fields |
| --- | --- |
| Identity | `pipeline_name`, `run_id`, `run_type`, `workflow_id`, `execution_context` |
| Replay / resume provenance | `replay_of_run_id`, `replay_of_manifest_id`, `resume_run_id`, `resume_manifest_id`, `exact_replay` |
| Control-plane anchors | `manifest_id`, `execution_fingerprint`, `config_hash`, `resolved_config_hash`, `effective_config_hash`, `source_fingerprint` |
| Contract/DQ identity | `contract_ref`, `contract_version`, `contract_schema_hash`, `dq_policy_ref`, `rule_bundle_version`, `contract_identity`, `dq_contract_compatibility`, `dq_contract_compatibility_hash` |
| Operator flags | `resume`, `dry_run`, `limit`, `query`, `start_offset`, `skip_gold`, `ignore_yaml_filter`, `tracing_enabled_override`, `debug_export_enabled` |
| Runtime options | `vacuum`, `input_filter`, `cached_bronze`, `required_persistence_profile`, `required_persistence_profile_opt_down` |

### Helper behavior

- `PipelineRunContext.create(...)` resolves `started_at` through the shared
  time seam instead of direct `datetime.now()`.
- Vacuum, input-filter, and cached-Bronze subcontexts are normalized through
  helper resolvers so the context always carries explicit value objects rather
  than loose `None`/dict state.
- Contract/DQ alignment is validated through helpers in
  `context_validation.py`.

## Helper Modules

| Module | Current live role |
| --- | --- |
| `context_time.py` | `ClockLike`, `MISSING_RUNTIME_TIMESTAMP`, `resolve_context_started_at()` |
| `context_validation.py` | Cross-checks contract identity completeness and DQ compatibility alignment |
| `context_correlation.py` | Normalizes optional correlation values to non-empty strings |
| `context_filtering.py` | Input-filter and vacuum option value objects |
| `context_cached_bronze.py` | Cached-Bronze enablement/path/date options |

## Determinism Boundary

- Context factories use `resolve_context_started_at()` from
  `context_time.py`.
- If `started_at` is omitted and no clock is provided, the deterministic
  sentinel `MISSING_RUNTIME_TIMESTAMP` is used instead of a wall-clock default.
- The time-seam regression contract is guarded by
  `tests/architecture/test_time_seam_normalization.py`.

## Related Tests

- `tests/architecture/test_domain_public_api.py`
- `tests/architecture/test_time_seam_normalization.py`

## Related References

- [Domain Reference](README.md)
- [Invariants](invariants.md)
- [API Reference: Domain](../api/domain.md)
