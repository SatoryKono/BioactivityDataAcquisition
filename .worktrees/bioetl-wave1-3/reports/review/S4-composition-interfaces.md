# S4 Code Review: Composition + Interfaces (Consolidated)

**Reviewer:** Claude Code (py-audit-bot mode)
**Date:** 2026-02-26
**Scope:** `src/bioetl/composition/` (54 files) + `src/bioetl/interfaces/` (29 files) = 83 files
**Rules:** `.claude/rules/ai-selfreview-rules.md`

---

## Executive Summary

| Sub-zone | Scope | Score | Status |
|----------|-------|-------|--------|
| S4.1 | composition/bootstrap/ + factories/ (29 files) | 9.2/10 | PASS |
| S4.2 | composition/ remaining (23 files) | 8.7/10 | PASS |
| S4.3 | interfaces/ (29 files) | 9.1/10 | PASS |
| **S4 Overall** | **83 files** | **9.0/10** | **PASS** |

The composition and interfaces layers are well-architected and follow the project's hexagonal architecture rules. Factory isolation (ARCH-005) is fully compliant. DI wiring uses constructor injection consistently. CLI commands follow the thin controller pattern with proper delegation to composition entrypoints. Click usage (EXC-008) and CLI confirmations (EXC-009) are correctly handled as documented exceptions.

---

## Architecture Compliance

### ARCH-001: Import Matrix -- PASS
No forbidden cross-layer imports detected across all 83 files:
- composition/ imports from domain, application, infrastructure (all allowed)
- interfaces/ imports from domain, application, infrastructure, composition (all allowed)
- No imports from interfaces/ into composition/
- No imports from composition/ or interfaces/ into domain/ or application/

### ARCH-005: Factory Isolation -- PASS
All factory and assembly logic resides exclusively in `composition/`:
- `GenericPipelineFactory` in `composition/factories/pipeline_factory.py`
- `DataSourceFactory` in `composition/factories/data_source_factory.py`
- `DQServicesFactory` in `composition/factories/dq_factory.py`
- `StorageFactory` in `composition/factories/storage.py`
- `FilterConfigBuilder` in `composition/builders.py`
- `MetadataCoordinator` in `composition/services/metadata_coordinator.py`
- All provider registrations in `composition/providers/registration.py`

No factory instantiations found outside composition/.

### ARCH-008: Single Source of Imports -- PASS
Port imports use the `bioetl.domain.ports` facade throughout:
```python
from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort, TracingPort
```

---

## DI Wiring Audit

### Constructor Injection -- PASS
All major components use constructor injection:
- `HealthServer.__init__(health_monitor, logger)` -- ports injected
- `ObservabilityBundle.__init__(logger, metrics, tracer, dq_monitor)` -- ports injected
- `MetadataCoordinator.__init__(run_context)` -- context injected
- All CLI commands delegate to `get_*_service()` entrypoints

### No Hard-coded Constructors -- PASS
No concrete dependencies created inside application or domain classes. All wiring happens in composition/:
```python
# composition/_services.py (typical pattern)
def get_checkpoint_service() -> CheckpointService:
    _ensure_registrations()
    return bootstrap_checkpoint_service()
```

### Side Effects at Module Level -- MINOR FINDINGS
- `providers/loader.py`: Module-level `_loaded = False` flag (idempotency pattern, has `reset_loader()` for tests)
- `registry.py`: Module-level `_default_registry = PipelineRegistry()` instance (well-documented, has `create_registry()` for test isolation)
- `bootstrap_logger.py`: Module-level `_bootstrap_logger: ... | None = None` cache (has `reset_bootstrap_logger()` for tests)

All have test reset mechanisms. Acceptable per EXC-015 and EXC-014.

---

## Findings Summary

### Findings by Severity

| ID | Severity | Rule | File | Description |
|----|----------|------|------|-------------|
| F-S4.2-001 | MEDIUM | AP-002 | `bootstrap_logger.py` | structlog import in composition layer |
| F-S4.2-002 | MEDIUM | DI-004 | `provider_registry.py` | ClassVar mutable dict as module-level state |
| F-S4.2-003 | LOW | DI-004 | `loader.py` | Module-level mutable `_loaded` flag |
| F-S4.3-001 | LOW | ARCH-001 | `observability.py` | Direct infrastructure import (permitted but inconsistent) |

### Finding Details

#### F-S4.2-001: structlog Import in Composition Layer (MEDIUM)
**File:** `composition/bootstrap_logger.py:27`
**Rule:** AP-002

`bootstrap_logger.py` directly imports `structlog` in the composition layer. Per AP-002, structlog should only be in `infrastructure/observability/`. The module provides bootstrap-phase logging before LoggerPort is available.

**Recommendation:** Move to `infrastructure/observability/bootstrap_logger.py` and import the wrapper from there.

#### F-S4.2-002: ClassVar Mutable State in ProviderRegistry (MEDIUM)
**File:** `composition/providers/provider_registry.py:121`
**Rule:** DI-004

```python
_providers: ClassVar[dict[str, ProviderConfig]] = {}
```

Class-level mutable dictionary. The instance-based `PipelineRegistry` pattern (with threading.RLock) is a better alternative already implemented in the codebase.

**Recommendation:** Consider migrating to instance-based pattern like `PipelineRegistry` for consistency and better test isolation.

#### F-S4.2-003: Module-level Mutable Flag (LOW)
**File:** `composition/providers/loader.py:12`

Module-level `_loaded = False` for idempotency. Has `reset_loader()` for tests. Standard pattern, minimal risk.

#### F-S4.3-001: Direct Infrastructure Import (LOW)
**File:** `interfaces/observability.py:14`

Imports `start_metrics_server` from infrastructure. While permitted by ARCH-001 for interfaces layer, inconsistent with other interfaces modules that route through composition entrypoints.

---

## Confirmed Exceptions (EXC)

| Exception | Files | Justification |
|-----------|-------|---------------|
| EXC-003 (NoOp Implementations) | bootstrap/cli/noop.py, runtime/observability.py | Null Object Pattern for NoOpLogger, NoOpMetrics, NoOpTracing |
| EXC-004 (Re-exports) | entrypoints.py, types.py, bootstrap_contexts.py | Backward compatibility re-exports with __all__ |
| EXC-008 (Click for CLI) | All cli/commands/*.py, cli/main.py | Intentional Click usage for CLI |
| EXC-009 (CLI Confirmations) | run_helpers.py, quarantine.py, run_all.py | click.confirm() in interfaces layer |
| EXC-012 (Domain imports in Infra) | N/A for S4 scope | Confirmed in cross-layer imports |
| EXC-013 (domain.types/exceptions) | exit_codes.py, quarantine.py, lock.py, health_server.py | domain.types.HealthStatus, RunType, etc. |
| EXC-015 (Config Classes with Defaults) | bootstrap_contexts.py, registry.py, _pipeline_execution.py | VacuumOptions, ArchiveOptions, DQOutputPathsContext |

---

## Naming and Typing Compliance

### NAME-001: Class Suffixes -- PASS
83 files reviewed. All classes follow naming conventions:
- Factory: GenericPipelineFactory, DataSourceFactory, StorageFactory, etc.
- Config: RuntimeConfig, HttpConfig, ProviderConfig, etc.
- Port: PipelineFactoryPort, DataSourceCreator (Protocol)
- Context: PipelineCallbacksContext, DQConfigsContext, etc.
- Service: (in application layer, correctly referenced)
- Error: ObservabilityContractError, PipelineNotFoundError (from application)
- Result: BatchRunResult, RunResult (from application)

### TYPE-001: Public Function Annotations -- PASS
All public functions across 83 files have complete return type annotations.

### TYPE-002: Any Usage -- PASS
All `Any` usages have inline justification comments:
- Callback signatures (`bootstrap_contexts.py`)
- Pandera DataFrameModel references (`registry.py`, `metadata_coordinator.py`)
- External API JSON responses (`formatters.py`)
- Pydantic model conversion (`config.py`)

---

## Positive Patterns Observed

1. **Injectable Function Parameters** -- `runtime/pipeline.py` passes bootstrap functions as parameters for testability
2. **Thread-safe Registry** -- `PipelineRegistry` uses RLock with deterministic ordering
3. **Observability Contract** -- `ObservabilityBundle.__post_init__` validates required components
4. **Coroutine Cleanup** -- CLI commands properly close coroutines in `finally` blocks
5. **Thin Controller Pattern** -- CLI commands have zero business logic, pure delegation
6. **Formatter Separation** -- `formatters.py` contains only pure presentation functions
7. **Exit Code Design** -- Comprehensive ExitCode enum with MRO-based exception mapping
8. **Health Server DI** -- HealthServer gets dependencies from composition root
9. **Idempotent Registration** -- `_ensure_registrations()` called before every service getter
10. **Deprecated Alias Management** -- Clear migration path from old to new function names

---

## Recommendations (Non-blocking)

1. **Move bootstrap_logger.py** to `infrastructure/observability/` to align with AP-002 (F-S4.2-001)
2. **Migrate ProviderRegistry** to instance-based pattern like PipelineRegistry for consistency (F-S4.2-002)
3. **Add @deprecated decorators** to deprecated aliases when Python 3.13 is adopted
4. **Consolidate error mappings** between `run.py:_map_status_to_exit_code()` and `exit_codes.py:EXCEPTION_EXIT_CODES`
5. **Add public accessors** on PipelineRunner for `_context` and `_executor` to avoid private attribute access in `_pipeline_execution.py`
6. **Translate Russian docstrings** in `provider_registry.py` and `decorators.py` to English for consistency

---

## Sub-zone Reports

- [S4.1 Bootstrap + Factories](./S4.1-bootstrap-factories.md)
- [S4.2 Composition Remaining](./S4.2-composition-remaining.md)
- [S4.3 Interfaces](./S4.3-interfaces.md)
