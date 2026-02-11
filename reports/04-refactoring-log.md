# Refactoring Log

## RF-RunStatus-Dedup: Resolve RunStatus enum duplication

**Date**: 2026-02-11
**Status**: done
**Layer**: domain

### Context

Two different `RunStatus` enums existed with different semantics:
- **A** (`domain/aggregates/pipeline_run.py`): Lifecycle state (PENDING, RUNNING, COMPLETED, FAILED, SHUTDOWN)
- **B** (`application/services/pipeline_runner_service.py`): Completion result (SUCCESS, SHUTDOWN, FAILED, DRY_RUN)

Only B was imported externally (composition, interfaces, tests). A was used solely within `pipeline_run.py` and its direct tests.

### Decision

Renamed A from `RunStatus` to `PipelineRunState` to eliminate name collision and clarify semantics. B remains unchanged as `RunStatus` since it is the widely-used public API.

### Changes

| File | Action | Description |
|------|--------|-------------|
| `src/bioetl/domain/aggregates/pipeline_run.py` | modified | Renamed `RunStatus` to `PipelineRunState`, updated all internal references |
| `src/bioetl/domain/aggregates/__init__.py` | modified | Updated import and `__all__` re-export |
| `tests/unit/domain/aggregates/test_pipeline_run.py` | modified | Updated all `RunStatus` references to `PipelineRunState` |
| `tests/architecture/test_aggregate_boundaries.py` | modified | Updated aggregate class registry |

### Verification

```bash
python -m pytest tests/unit/domain/aggregates/test_pipeline_run.py -x -q  # 27 passed
python -m pytest tests/architecture/test_aggregate_boundaries.py -x -q    # 8 passed
python -m pytest tests/unit/application/services/test_pipeline_runner_service.py -x -q  # 24 passed
```
