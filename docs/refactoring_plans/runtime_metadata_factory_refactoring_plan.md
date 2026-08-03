# Refactoring Plan: RuntimeMetadataFactory/RuntimeMetadataProtocol Naming Consistency

## Overview

This plan addresses naming inconsistencies where "Factory" aliases exist for Protocol classes without actual factory implementations. The goal is to align naming with actual behavior and project conventions.

## Current Issues Identified

### 1. RuntimeMetadataFactory/RuntimeMetadataProtocol

- **Problem:** `RuntimeMetadataProtocol` exists but no `RuntimeMetadataFactory` class
- **Issue:** Parameter named `runtime_metadata_factory` suggests factory pattern
- **Location:** `src/bioetl/application/services/lineage/metadata_assemblers_helpers.py`

### 2. PipelineMetadataFactory/PipelineMetadataProtocol

- **Problem:** `PipelineMetadataProtocol` exists but no `PipelineMetadataFactory` class
- **Issue:** Parameter named `pipeline_metadata_factory` suggests factory pattern
- **Location:** `src/bioetl/application/services/lineage/metadata_assemblers_helpers.py`

### 3. DomainEventEmitter/DomainEventEmitterPort

- **Problem:** Only `DomainEventEmitterPort` exists, no alias
- **Issue:** Inconsistent with other Port implementations
- **Location:** `src/bioetl/application/observability/domain_event_emitter.py`

### 4. RunExecutionRequest/RunExecutionContext

- **Status:** Completed on `2026-05-08`
- **Resolution:** `RunExecutionRequest` is the sole canonical execution request
  type; the temporary `RunExecutionContext` compatibility export has been removed
- **Location:** `src/bioetl/application/services/execution/cli_run_orchestration_models.py`

## Refactoring Plan

### Phase 1: Protocol/Factory Naming Consistency

**Objective:** Rename protocols to use "Port" suffix and update parameter names

**Files to modify:**

- `src/bioetl/application/services/lineage/metadata_assemblers_helpers.py`
- `src/bioetl/application/services/lineage/metadata_assemblers.py`

**Specific changes:**

1. Rename `RuntimeMetadataProtocol` → `RuntimeMetadataPort`
1. Rename `PipelineMetadataProtocol` → `PipelineMetadataPort`
1. Update parameter names:
   - `runtime_metadata_factory` → `runtime_metadata_port`
   - `pipeline_metadata_factory` → `pipeline_metadata_port`
1. Update `__all__` exports
1. Update docstrings

**Rationale:** Follows established pattern of using "Port" suffix for protocols/interfaces, removes misleading "Factory" implication.

### Phase 2: DomainEventEmitter Cleanup

**Objective:** Ensure consistent usage of DomainEventEmitterPort

**Files to modify:**

- `src/bioetl/application/observability/domain_event_emitter.py`
- All files importing domain event emitter

**Specific changes:**

1. Verify no `DomainEventEmitter` alias exists
1. Ensure all imports use `DomainEventEmitterPort`
1. Update type hints if needed

**Rationale:** Enforces consistent Port suffix usage.

### Phase 3: RunExecutionRequest/RunExecutionContext Unification

**Objective:** Standardize on single, semantically accurate name

**Status:** Completed on `2026-05-08`

**Files to modify:**

- `src/bioetl/application/services/execution/cli_run_orchestration_models.py`
- All files importing these classes

**Specific changes:**

1. Remove `RunExecutionRequest` alias
1. Rename `RunExecutionContext` → `RunExecutionRequest`
1. Update all imports and type hints
1. Update `__all__` export

**Rationale:** `RunExecutionRequest` better describes CLI execution request semantics.

### Phase 4: Additional Consistency Fixes

**Objective:** Apply consistent naming patterns across similar cases

**Patterns to standardize:**

1. **CompositeRunnerDependencies/CompositeRunnerDependencyGroup** → Use plural form consistently
1. **CompositePipelineFinalizationRequest/CompositePipelineFinalizationContext** → Choose consistent suffix
1. **PolarsJoinAdapter/JoinExecutorService** → Remove misleading adapter alias or implement real adapter

## Implementation Checklist

```markdown
- [ ] Phase 1: Rename protocols to use "Port" suffix
  - [ ] Rename RuntimeMetadataProtocol → RuntimeMetadataPort
  - [ ] Rename PipelineMetadataProtocol → PipelineMetadataPort
  - [ ] Update parameter names (factory → port)
  - [ ] Update __all__ exports
  - [ ] Update docstrings

- [ ] Phase 2: DomainEventEmitter cleanup
  - [ ] Verify no alias exists
  - [ ] Ensure consistent usage of DomainEventEmitterPort

- [x] Phase 3: RunExecutionRequest/RunExecutionContext unification
  - [x] Remove RunExecutionRequest alias
  - [x] Rename RunExecutionContext → RunExecutionRequest
  - [x] Update all imports and usage
  - [x] Update __all__ exports

- [ ] Phase 4: Additional consistency fixes
  - [ ] Standardize CompositeRunnerDependencies naming
  - [ ] Unify CompositePipelineFinalization* suffixes
  - [ ] Resolve PolarsJoinAdapter/JoinExecutorService
```

## Verification Steps

1. **Static Analysis:**

   ```bash
   mypy --strict src/bioetl/
   ```

1. **Testing:**

   ```bash
   pytest tests/ -x -q
   ```

1. **Import Verification:**

   - Check no import errors
   - Verify all references updated
   - Confirm naming follows conventions

## Expected Benefits

1. **Clarity:** Names accurately reflect actual implementation
1. **Consistency:** Uniform use of "Port" suffix for protocols
1. **Maintainability:** Reduced cognitive load from misleading aliases
1. **Standards Compliance:** Aligns with project naming conventions

## Risk Assessment

**Risk Level:** Low

**Mitigation:**

- Changes are primarily renaming without behavior changes
- Follows existing patterns in codebase
- Comprehensive testing coverage
- Type checking ensures correctness

## Timeline Estimate

- **Phase 1:** 1-2 hours
- **Phase 2:** 30 minutes
- **Phase 3:** 1-2 hours
- **Phase 4:** 2-3 hours
- **Total:** 5-7 hours

## Rollback Plan

If issues arise, changes can be easily reverted as they are primarily textual replacements without logic changes.
