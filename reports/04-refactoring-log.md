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

---

## RF-ENTITY: Resolve entity class name duplication between domain and infrastructure

**Date**: 2026-02-11
**Status**: done
**Layer**: infrastructure

### Context

Two pairs of entity classes shared the same name across domain and infrastructure layers:

1. **ChemblPublicationRecord** existed in both:
   - `domain/entities/chembl.py` (domain DTO, `extra="forbid"`, `frozen=True`, flat `chembl_release: str`)
   - `infrastructure/adapters/chembl/models.py` (API response model, `extra="ignore"`, nested `chembl_release: ChemblReleaseInfo`)

2. **PubchemMoleculeRecord** existed in both:
   - `domain/entities/pubchem.py` (domain DTO, `extra="forbid"`, `cid: str`, 35+ fields)
   - `infrastructure/adapters/pubchem/models.py` (API response model, `extra="ignore"`, `cid: int`, ~15 fields)

The naming collision created ambiguity about which class was being referenced. Fields and semantics differed significantly in both cases.

### Decision

Renamed the infrastructure versions to include `Api` suffix:
- `ChemblPublicationRecord` -> `ChemblPublicationApiRecord` (infrastructure)
- `PubchemMoleculeRecord` -> `PubchemMoleculeApiRecord` (infrastructure)

Domain versions remain unchanged as the canonical entity names. The client adapters (chembl/client.py, pubchem/client.py) already imported from domain, so no changes were needed there.

### Changes

| File | Action | Description |
|------|--------|-------------|
| `src/bioetl/infrastructure/adapters/chembl/models.py` | modified | Renamed `ChemblPublicationRecord` to `ChemblPublicationApiRecord`; updated `ChemblPublicationResponse.documents` type hint; updated `CHEMBL_RECORD_MODELS` dict |
| `src/bioetl/infrastructure/adapters/chembl/__init__.py` | modified | Updated import and `__all__` re-export |
| `src/bioetl/infrastructure/adapters/pubchem/models.py` | modified | Renamed `PubchemMoleculeRecord` to `PubchemMoleculeApiRecord`; updated `PUBCHEM_RECORD_MODELS` dict |
| `src/bioetl/infrastructure/adapters/pubchem/__init__.py` | modified | Updated import and `__all__` re-export |

### Verification

```bash
python -c "from bioetl.infrastructure.adapters.chembl.models import ChemblPublicationApiRecord, CHEMBL_RECORD_MODELS"  # OK
python -c "from bioetl.infrastructure.adapters.pubchem.models import PubchemMoleculeApiRecord, PUBCHEM_RECORD_MODELS"  # OK
python -c "from bioetl.domain.entities.chembl import ChemblPublicationRecord"  # Domain unchanged
python -c "from bioetl.domain.entities.pubchem import PubchemMoleculeRecord"  # Domain unchanged
python -m pytest tests/architecture/ -q --deselect tests/architecture/test_code_metrics.py::TestFileSizeLimits::test_domain_files_under_limit  # 3 pre-existing noop_tracing failures only
python -m ruff check --select I src tests  # All checks passed
```

---

## RF-NoOp-Consolidate: Consolidate duplicate NoOp implementations

**Date**: 2026-02-11
**Status**: done
**Layer**: infrastructure

### Context

Two parallel hierarchies of NoOp implementations existed:

- **A** (`domain/ports/noop.py`, 470 LOC): NoOpTracing, NoOpMetrics, NoOpAudit, NoOpPiiHasher, NoOpMemoryMonitor, NoOpMetadataWriter
- **B** (`infrastructure/observability/`): noop_logger.py (NoOpLogger), noop_metrics.py (NoOpMetrics), noop_tracing.py (NoOpTracing)

NoOpTracing and NoOpMetrics were duplicated across both locations. Per ARCH-001, domain cannot import from infrastructure, so domain/ports/noop.py is the canonical source of truth.

The infrastructure NoOpMetrics had extra functionality (`warn_on_use`, `reset_warning`) used by composition layer code.

### Decision

1. **NoOpTracing**: Replaced infrastructure `noop_tracing.py` (61 LOC) with a re-export from `domain.ports` facade (14 LOC). No API change.
2. **NoOpMetrics**: Replaced infrastructure `noop_metrics.py` (89 LOC) with a thin subclass (61 LOC) inheriting all no-op methods from domain `NoOpMetrics` while preserving `warn_on_use`/`reset_warning` API for composition consumers.
3. **NoOpLogger**: Left in infrastructure (no domain counterpart; LoggerPort impl is infra responsibility).
4. **`__init__.py`**: No changes needed -- existing imports from `noop_metrics.py`/`noop_tracing.py` still resolve correctly.
5. All imports use the `bioetl.domain.ports` facade per ARCH-008 (not internal `bioetl.domain.ports.noop`).

### Changes

| File | Action | Description |
|------|--------|-------------|
| `src/bioetl/infrastructure/observability/noop_tracing.py` | modified | Replaced 61 LOC duplicate with 14 LOC re-export from `bioetl.domain.ports` |
| `src/bioetl/infrastructure/observability/noop_metrics.py` | modified | Replaced 89 LOC duplicate with 61 LOC subclass inheriting from domain NoOpMetrics; preserves `warn_on_use`/`reset_warning` |

### Verification

```bash
python -m pytest tests/infrastructure/observability/test_metrics.py -v -q  # 8 passed
python -m pytest tests/unit/infrastructure/observability/test_tracing.py -v -q  # 20 passed
python -m pytest tests/unit/composition/test_observability_contract.py -v -q  # 25 passed
python -m pytest tests/architecture/test_forbidden_imports.py::TestPortImportFacade -v -q  # 1 passed
python -m pytest tests/test_architecture.py::test_metrics_implementations_are_compliant -v -q  # 1 passed
python -m pytest tests/ --timeout=120 --ignore=tests/architecture/test_column_order.py --ignore=tests/architecture/test_config_golden_master.py --ignore=tests/architecture/test_code_metrics.py --ignore=tests/architecture/test_domain_purity.py --tb=no  # 11331 passed, 213 skipped
```
