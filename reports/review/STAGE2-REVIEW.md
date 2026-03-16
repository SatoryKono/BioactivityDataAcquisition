# BioETL Stage 2 Architectural Review
**Date**: 2026-03-16
**Task**: STAGE2-REVIEW
**Scope**: Stage 1 changed files (RF-007.3, RF-006.1, RF-008.2, RF-007.1) with full project context
**Reviewer**: Claude Opus 4.6

---

## Files Under Review

| RF | File | Layer |
|----|------|-------|
| RF-007.3 | `src/bioetl/domain/ports/storage_maintenance.py` | domain |
| RF-007.3 | `src/bioetl/composition/factories/storage/maintenance_mixin.py` | composition |
| RF-007.3 | `src/bioetl/application/core/postrun/metadata_version_resolver.py` | application |
| RF-007.3 | `src/bioetl/composition/factories/pipeline/postrun_assembly.py` | composition |
| RF-007.3 | `tests/architecture/test_layer_dependencies.py` | tests |
| RF-006.1 | `src/bioetl/application/composite/runner_pkg/runner_models.py` | application |
| RF-006.1 | `src/bioetl/application/composite/runner_pkg/runner.py` | application |
| RF-008.2 | `src/bioetl/application/composite/merger.py` | application |
| RF-008.2 | `tests/architecture/test_narrow_port_migration.py` | tests |
| RF-007.1 | `src/bioetl/application/composite/coordinator.py` | application |
| RF-007.1 | `src/bioetl/application/composite/coordinator_result_mixin.py` | application |

---

## Category Scores

### 1. Layer Isolation (ARCH-001) -- Score: 9.5/10 | Weight: 15%

**Observations:**
- Import matrix is fully respected across all changed files. Application layer imports only from `bioetl.domain.*` -- verified via grep that zero `from bioetl.infrastructure` imports exist in `src/bioetl/application/`.
- Infrastructure does not import application. Composition correctly imports from all inner layers (domain, application, infrastructure).
- All port imports in application composite modules use the facade `bioetl.domain.ports` (not internal sub-modules like `bioetl.domain.ports.storage_maintenance`).

**Issues:**
- (LOW) `StorageMaintenancePort` is defined in `domain/ports/storage_maintenance.py` but re-exported via `domain/ports/storage/__init__.py`. Two internal imports bypass the top-level facade (`domain/ports/storage/__init__.py` and `domain/ports/storage/aggregate_port.py` import directly from `storage_maintenance`). This is acceptable for intra-package wiring but worth noting as a minor ARCH-008 edge case within the ports package itself.

**Deduction:** -0.25 (1 LOW)
**Weighted contribution:** 9.5 x 0.15 = 1.425

---

### 2. Domain Purity (ARCH-002) -- Score: 10.0/10 | Weight: 10%

**Observations:**
- `StorageMaintenancePort` in domain is a pure Protocol definition. No I/O, no structlog, no file operations, no HTTP clients.
- Port uses only `pathlib.Path` (type annotation) and `typing` primitives. `Path` in return type is a domain concept (resolved path) -- not I/O itself.
- Domain constants (`DEFAULT_LOCK_TTL_SECONDS`) are pure immutable values.
- `from __future__ import annotations` present in all reviewed domain files.

**Issues:** None.

**Deduction:** 0
**Weighted contribution:** 10.0 x 0.10 = 1.000

---

### 3. Dependency Injection -- Score: 9.0/10 | Weight: 12%

**Observations:**
- `PostrunMetadataVersionResolver` exemplifies correct DI: all collaborators (`logger`, `runtime`, `storage`, `warning_allowlist`) are constructor-injected via keyword-only arguments.
- `EnrichmentCoordinatorService` injects `logger`, `dq_config`, and an optional `semaphore_factory` -- excellent testability.
- `CompositePipelineRunner` has a large constructor (18 parameters) but all dependencies are injected. No hard-coded constructors detected.
- `MergeService` uses a `MergeCollaboratorGroup` bundle pattern to reduce constructor width -- good DI ergonomics.

**Issues:**
- (MEDIUM) `CompositePipelineRunner.__init__` has 18 parameters. While all are injected (no DI violation), the parameter count suggests the class may be coordinating too many concerns. The mixin decomposition (`StageMixin`, `ObservabilityMixin`, etc.) mitigates this, but the constructor remains a cognitive burden. Consider a `CompositeRunnerDependencies` dataclass bundle similar to `MergeCollaboratorGroup`.
- (LOW) `maintenance_mixin.py` line 84 uses `datetime.now(UTC)` inside the composition layer. Per RULES.md section 4.3, timestamps should be passed from application. However, this is in a maintenance operation (not pipeline data flow), so the determinism concern is reduced.

**Deduction:** -0.75 (1 MEDIUM + 1 LOW)
**Weighted contribution:** 9.0 x 0.12 = 1.080

---

### 4. Port/Adapter Contracts -- Score: 9.5/10 | Weight: 12%

**Observations:**
- `StorageMaintenancePort` is a well-decomposed narrow port (RF-007.3 goal achieved). It covers vacuum, optimize, archive, deduplicate, clear, and version resolution -- all maintenance-specific operations separated from read/write storage ports.
- The port is `@runtime_checkable` (TYPE-004 compliance).
- `MergeService` now uses `MergedStoragePort` instead of broad `StoragePort` (RF-008.2 confirmed by narrow port migration test).
- Architecture test `test_narrow_port_migration.py` enforces a ratchet budget of 4 files maximum using broad `StoragePort` -- excellent migration guardrail.
- `ExecutionMetricsRunnerPort` and `ExecutionMetricsReadablePort` are properly separated (read vs run concerns).

**Issues:**
- (LOW) `StorageMaintenancePort.get_table_path` returns `Path` -- a concrete type from `pathlib`. While pragmatic, a truly infrastructure-agnostic port might return `str`. This is a minor design trade-off that is acceptable given the local-filesystem-only deployment model (ADR-010).

**Deduction:** -0.25 (1 LOW)
**Weighted contribution:** 9.5 x 0.12 = 1.140

---

### 5. Error Handling & Resilience -- Score: 9.0/10 | Weight: 10%

**Observations:**
- `coordinator.py` implements fail-fast semantics for required enrichers: `asyncio.gather` without `return_exceptions` means required enricher failures propagate immediately and cancel siblings. Optional enrichers are caught and returned as `FAILED` results. This is a clean, well-documented design (RF-007.1).
- `PostrunMetadataVersionResolver` uses configurable `warning_allowlist` tuple for exception handling -- strict mode re-raises, lenient mode returns `None`. Excellent for operational flexibility.
- `maintenance_mixin.py` `get_table_version` catches `(OSError, RuntimeError, ValueError, ImportError)` and returns `None` -- safe fallback for missing tables.
- `_ENRICHER_EXECUTION_ERRORS` and `_FILTER_CONDITION_ERRORS` are well-curated exception groups.

**Issues:**
- (MEDIUM) In `coordinator_result_mixin.py` line 159, `_handle_enricher_error` calls `raise` (bare re-raise) for required enrichers, but the method signature returns `EnrichmentResult`. A reader might expect it to always return a result. The control flow is correct (re-raise propagates through `asyncio.gather`), but a type-checker might warn about unreachable code after `raise`. Consider adding `# type: ignore[return-value]` or restructuring to make the never-returns path explicit (e.g., `raise` in a separate method).
- (LOW) `maintenance_mixin.py` `vacuum()` catches `DeltaTable` constructor exceptions implicitly via the `_is_delta_table_dir` guard, but if `DeltaTable(str(gold_table_path))` raises on a corrupted log, it will propagate unhandled. The caller should handle this.

**Deduction:** -0.75 (1 MEDIUM + 1 LOW)
**Weighted contribution:** 9.0 x 0.10 = 0.900

---

### 6. Naming & Conventions -- Score: 9.5/10 | Weight: 8%

**Observations:**
- All classes follow NAME-001 suffixes: `StorageMaintenancePort`, `PostrunMetadataVersionResolver`, `EnrichmentCoordinatorService`, `MergeService`, `CompositeRuntimeConfig`, `CompositePipelineRunner`.
- `CompositePipelineRunnerService` alias preserved for backward compatibility (documented inline).
- Module naming is descriptive snake_case: `metadata_version_resolver.py`, `coordinator_result_mixin.py`, `runner_models.py`.
- Private attributes consistently use single underscore prefix (`self._logger`, `self._storage`, etc.).
- Constants are UPPER_SNAKE_CASE: `DEFAULT_LOCK_TTL_SECONDS`, `_COMPOSITE_HEARTBEAT_INTERVAL_SECONDS`.

**Issues:**
- (LOW) `_COMPOSITE_HEARTBEAT_INTERVAL_SECONDS` in `runner.py` line 41 is marked deprecated but still present. Dead constant should be removed to avoid confusion.

**Deduction:** -0.25 (1 LOW)
**Weighted contribution:** 9.5 x 0.08 = 0.760

---

### 7. Type Safety -- Score: 9.0/10 | Weight: 10%

**Observations:**
- All public methods have full type annotations including return types.
- `StorageMaintenancePort` uses `Literal["silver", "gold"]` for layer parameters -- strong type narrowing.
- `CompositeRuntimeConfig` is a frozen dataclass with typed defaults and a `__post_init__` that normalizes `list` to `tuple` for immutability.
- `from __future__ import annotations` present in all files -- PEP 604 union syntax (`str | None`) used consistently.
- `coordinator_result_mixin.py` uses `JsonDict` type alias for structured log kwargs.

**Issues:**
- (MEDIUM) `PostrunMetadataVersionResolver.__init__` declares `runtime: object` -- an overly broad type. This loses type information; callers pass `RuntimeConfig` but the resolver only uses `getattr(self._runtime, "strict_validation", False)`. A protocol or `RuntimeConfig` type hint would be safer.
- (LOW) `maintenance_mixin.py` `is_table_initialized` and `get_table_version` accept `layer: str` instead of `Literal["silver", "gold"]` as defined in the port. The mixin should match the port's type constraint.

**Deduction:** -0.75 (1 MEDIUM + 1 LOW)
**Weighted contribution:** 9.0 x 0.10 = 0.900

---

### 8. Testability -- Score: 9.5/10 | Weight: 8%

**Observations:**
- `test_layer_dependencies.py` provides comprehensive architecture guard tests: domain purity, import matrix enforcement, dead code detection, orphan directory checks. This is an excellent safety net.
- `test_narrow_port_migration.py` uses a ratchet pattern (`_MAX_BROAD_STORAGE_PORT_FILES = 4`) -- a pragmatic approach to incremental migration that prevents regression while allowing gradual cleanup.
- `EnrichmentCoordinatorService` accepts a `semaphore_factory` parameter -- explicitly designed for test injection.
- `PostrunMetadataVersionResolver` with injectable `warning_allowlist` tuple enables testing of strict vs lenient behavior.
- `build_postrun_dependency_context()` factory function in `postrun_assembly.py` enables both production and test construction.

**Issues:**
- (LOW) `test_layer_dependencies.py` `test_import_linter_contracts` has multiple skip conditions for Windows/encoding issues. This means the test may silently skip in CI on Windows, reducing coverage confidence.

**Deduction:** -0.25 (1 LOW)
**Weighted contribution:** 9.5 x 0.08 = 0.760

---

### 9. Configuration Management -- Score: 9.5/10 | Weight: 7%

**Observations:**
- `CompositeRuntimeConfig` is a frozen, slotted dataclass with sensible defaults (`heartbeat_interval_seconds=30`, `lock_ttl_seconds=DEFAULT_LOCK_TTL_SECONDS`). Immutability after construction is enforced by `frozen=True`.
- Heartbeat interval and lock TTL are now configurable (RF-006.1) instead of hardcoded, eliminating the need for the deprecated `_COMPOSITE_HEARTBEAT_INTERVAL_SECONDS` constant.
- `_POSTRUN_WARNING_ALLOWLIST` and `_METADATA_VERSION_ALLOWLIST` in `postrun_assembly.py` centralize exception policy -- single source of truth for what exceptions are tolerated.

**Issues:**
- (LOW) `_METADATA_VERSION_ALLOWLIST` includes `TypeError` -- it is unusual for a Delta table version resolution to raise `TypeError`. This may be overly broad. Consider whether this was added defensively or from a real failure scenario.

**Deduction:** -0.25 (1 LOW)
**Weighted contribution:** 9.5 x 0.07 = 0.665

---

### 10. Code Quality & Maintainability -- Score: 9.0/10 | Weight: 8%

**Observations:**
- Mixin decomposition in the composite runner (`StageMixin`, `ObservabilityMixin`, `MergeStageMixin`, `SupportMixin`) keeps individual files focused. The runner facade delegates stage logic cleanly.
- `MergeService` delegates to `execute_merge_workflow()` -- the facade pattern keeps the class focused on initialization while workflow logic lives in a separate module.
- Docstrings are thorough: `CompositePipelineRunner.__init__` has per-parameter documentation. `StorageMaintenancePort` methods have Args/Returns documentation.
- `coordinator.py` module docstring explains fail-fast semantics with a reference to RF-007.1.

**Issues:**
- (MEDIUM) `maintenance_mixin.py` uses lazy `from deltalake import DeltaTable` inside method bodies (lines 54 and 127). While this avoids import-time dependency, it means every `vacuum()` / `get_table_version()` call pays import overhead. A module-level guarded import or a one-time cached import would be better.
- (LOW) `runner.py` re-exports `CompositeExecutionContext` and `CompositeRuntimeConfig` in `__all__` even though they are defined in `runner_models.py`. This creates two import paths for the same classes. Consider importing from `runner_models` as the canonical path.

**Deduction:** -0.75 (1 MEDIUM + 1 LOW)
**Weighted contribution:** 9.0 x 0.08 = 0.720

---

## Scoring Summary

| # | Category | Weight | Raw Score | Deductions | Weighted |
|---|----------|--------|-----------|------------|----------|
| 1 | Layer Isolation | 15% | 10 | -0.25 | 1.425 |
| 2 | Domain Purity | 10% | 10 | 0 | 1.000 |
| 3 | Dependency Injection | 12% | 10 | -0.75 | 1.080 |
| 4 | Port/Adapter Contracts | 12% | 10 | -0.25 | 1.140 |
| 5 | Error Handling | 10% | 10 | -0.75 | 0.900 |
| 6 | Naming & Conventions | 8% | 10 | -0.25 | 0.760 |
| 7 | Type Safety | 10% | 10 | -0.75 | 0.900 |
| 8 | Testability | 8% | 10 | -0.25 | 0.760 |
| 9 | Configuration | 7% | 10 | -0.25 | 0.665 |
| 10 | Code Quality | 8% | 10 | -0.75 | 0.720 |
| **TOTAL** | | **100%** | | | **9.35** |

**Overall Status: PASS (9.35/10.0)**

---

## Top-3 Issues

### Issue 1: `PostrunMetadataVersionResolver.runtime` typed as `object` (MEDIUM)
- **File**: `src/bioetl/application/core/postrun/metadata_version_resolver.py:23`
- **Rule**: TYPE-001/TYPE-002
- **Impact**: Loses type information. `getattr(obj, "strict_validation", False)` is duck-typing on what should be a typed contract.
- **Fix**: Define a minimal Protocol or use `RuntimeConfig` directly.
```python
# Option A: Protocol
class _StrictValidationConfig(Protocol):
    strict_validation: bool

# Option B: Direct type
from bioetl.domain.config import RuntimeConfig
```

### Issue 2: `CompositePipelineRunner` constructor width (MEDIUM)
- **File**: `src/bioetl/application/composite/runner_pkg/runner.py:87-111`
- **Rule**: Code Quality / Maintainability
- **Impact**: 18 constructor parameters create cognitive overhead and fragile wiring.
- **Fix**: Bundle related dependencies into a `CompositeRunnerDependencies` dataclass, following the pattern already established by `MergeCollaboratorGroup`.

### Issue 3: Lazy `deltalake` import in hot path (MEDIUM)
- **File**: `src/bioetl/composition/factories/storage/maintenance_mixin.py:54,127`
- **Rule**: Code Quality
- **Impact**: Repeated `from deltalake import DeltaTable` on each call to `get_table_version()` and `vacuum()`.
- **Fix**: Use a module-level guarded import or cache the import result.
```python
_DeltaTable: type | None = None
def _get_delta_table_class() -> type:
    global _DeltaTable
    if _DeltaTable is None:
        from deltalake import DeltaTable
        _DeltaTable = DeltaTable
    return _DeltaTable
```

---

## Refactoring Plan

### Context and Strategic Assessment

The Stage 1 changes (RF-006.1, RF-007.1, RF-007.3, RF-008.2) demonstrate a mature architectural sensibility. The narrow port migration (RF-008.2), configurable heartbeat/TTL (RF-006.1), fail-fast enricher semantics (RF-007.1), and Delta Lake leak fix via `StorageMaintenancePort` (RF-007.3) are all well-executed. The codebase scores 9.35/10, placing it firmly in PASS territory. The issues identified are refinements, not structural defects. The following plan addresses them in priority order.

### Phase 1: Type Safety Tightening (Est. 2-3 hours)

**1a. Replace `runtime: object` with a Protocol in `PostrunMetadataVersionResolver`.**

The `metadata_version_resolver.py` file uses `getattr(self._runtime, "strict_validation", False)` to access a field on an untyped `object`. This is the single most impactful type safety improvement because it eliminates duck-typing at the application layer boundary. Define a minimal `StrictValidationAware` protocol in `domain/config/` or directly in the resolver module:

```python
class StrictValidationAware(Protocol):
    strict_validation: bool
```

Then change the constructor signature from `runtime: object` to `runtime: StrictValidationAware`. This preserves flexibility (any object with `strict_validation: bool` satisfies it) while giving mypy full visibility. The `RuntimeConfig` dataclass already has this field, so no adapter changes are needed. Update the `postrun_assembly.py` call site -- it already passes `RuntimeConfig`, so this is type-narrowing only.

**1b. Align `maintenance_mixin.py` type annotations with port definition.**

The mixin methods `is_table_initialized(layer: str)` and `get_table_version(layer: str)` accept bare `str` where the port specifies `Literal["silver", "gold"]`. Change to:

```python
from typing import Literal
def is_table_initialized(self, table_name: str, layer: Literal["silver", "gold"] = "silver") -> bool:
```

This is a mechanical change with zero runtime impact but ensures mypy catches invalid layer names at call sites.

### Phase 2: Constructor Width Reduction (Est. 3-4 hours)

**2a. Introduce `CompositeRunnerDependencies` bundle for `CompositePipelineRunner`.**

The runner currently accepts 18 parameters. Group them into a frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class CompositeRunnerDependencies:
    key_extractor: KeyExtractorService
    coordinator: EnrichmentCoordinatorService
    merger: MergeService
    checkpoint_manager: CompositeCheckpointManager
    fsm_state_helper: FSMStateHelperService
    dependency_coordinator: DependencyCoordinatorService | None = None
    preflight_validator: CompositePreflightValidator | None = None
    dq_report_service: DQReportService | None = None
    quarantine_port: QuarantinePort | None = None
    metrics: MetricsPort | None = None
```

This reduces the constructor from 18 to roughly 8 parameters (config, runtime, seed_runner_factory, enricher_runner_factory, dependencies_runner_factory, logger, lock, deps_bundle). The pattern is already proven by `MergeCollaboratorGroup`. The composition layer (`CompositeFactory`) already assembles these collaborators -- it would simply construct the bundle before passing it to the runner.

The key benefit is not just readability: it makes the dependency graph explicit and testable as a unit. Test fixtures can construct a `CompositeRunnerDependencies` with NoOp implementations and override individual fields.

**2b. Remove deprecated `_COMPOSITE_HEARTBEAT_INTERVAL_SECONDS` constant.**

Now that `CompositeRuntimeConfig.heartbeat_interval_seconds` is the canonical source (RF-006.1), the module-level constant at `runner.py:41` serves no purpose. Remove it and verify no references remain (grep confirms only the definition site uses it).

### Phase 3: Import and Performance Optimization (Est. 1-2 hours)

**3a. Cache the `deltalake.DeltaTable` import in `maintenance_mixin.py`.**

The current pattern of `from deltalake import DeltaTable` inside method bodies means Python's import machinery runs on every call. While Python caches imports in `sys.modules`, the lookup and attribute resolution still has measurable overhead on hot paths (vacuum is called per-table during maintenance sweeps). Introduce a module-level lazy cache:

```python
_DeltaTable: type | None = None

def _delta_table_cls() -> type:
    global _DeltaTable
    if _DeltaTable is None:
        from deltalake import DeltaTable
        _DeltaTable = DeltaTable
    return _DeltaTable
```

Then replace `DeltaTable(...)` calls with `_delta_table_cls()(...)`. This preserves the lazy-import behavior (composition layer does not hard-depend on deltalake at import time) while eliminating repeated import overhead.

**3b. Consolidate `runner_models.py` re-exports.**

`runner.py` re-exports `CompositeExecutionContext` and `CompositeRuntimeConfig` in its `__all__`. This creates two canonical import paths. Either remove the re-exports from `runner.py.__all__` (breaking change if external consumers import from `runner`) or add a deprecation notice. Since this is an internal module (`runner_pkg`), removing the re-exports and updating any internal consumers to import from `runner_models` directly is the cleaner path.

### Phase 4: Error Handling Refinement (Est. 1 hour)

**4a. Add DeltaTable corruption guard in `vacuum()`.**

The `vacuum()` method in `maintenance_mixin.py` constructs `DeltaTable(str(gold_table_path))` on line 132 without a try/except. If the Delta log is corrupted, this will raise an unhandled exception. Add a guard:

```python
try:
    dt = await loop.run_in_executor(None, lambda: DeltaTable(str(gold_table_path)))
except (OSError, RuntimeError, ValueError) as exc:
    # Log warning and skip Gold vacuum for corrupted table
    return total_removed
```

**4b. Review `_METADATA_VERSION_ALLOWLIST` for `TypeError`.**

Audit whether `TypeError` has ever been raised in Delta version resolution. If not, remove it from the allowlist to avoid masking genuine programming errors. The allowlist should contain only exceptions that represent expected operational conditions (missing table, permission errors), not logic errors.

### Summary

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| Phase 1: Type Safety | 2-3h | HIGH (eliminates duck-typing, mypy compliance) | P1 |
| Phase 2: Constructor Width | 3-4h | MEDIUM (readability, testability) | P2 |
| Phase 3: Import/Perf | 1-2h | LOW-MEDIUM (cleanup, marginal perf) | P3 |
| Phase 4: Error Handling | 1h | LOW (defensive hardening) | P3 |

Total estimated effort: 7-10 hours. All changes are backward-compatible and can be done incrementally without affecting existing tests. Phase 1 should be prioritized as it addresses the only type-system gap in the reviewed code.
