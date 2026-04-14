# TD-05: Decompose or Retire Merge Input Mixin Stack

**Status**: Open  
**Priority**: P1  
**Labels**: `technical-debt`, `refactoring`, `merge`, `legacy`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

The `merger_input_mixin.py` and `_MergeInputLoaderMixin` show:
- High removable complexity
- Zero-anchor retirement signals
- Legacy silver compatibility concerns

This suggests the mixin contains both live merge-input functionality and obsolete silver layer compatibility code.

## Root Cause

Historical evolution of merge architecture has led to:
- Accumulation of legacy compatibility layers
- Mixing of concerns (live vs legacy)
- Complex inheritance hierarchies
- Difficulty in testing and maintenance

## Scope

**Primary Files:**
- `src/bioetl/application/composite/merger_input_mixin.py`
- Related merge service files

**Impact Analysis:**
```bash
# Find all merge input usages
grep -rn "_MergeInputLoaderMixin\|from.*merger_input_mixin" src/ --include="*.py"

# Check test coverage
pytest --cov=src/bioetl/application/composite/merger_input_mixin.py --cov-report=term --dry-run
```

## Solution Plan

### Phase 1: Analysis (2 days)
1. **Code Separation Analysis**
   ```bash
   # Identify live vs legacy code
   grep -rn "silver\|legacy\|compat" src/bioetl/application/composite/merger_input_mixin.py
   ```

2. **Usage Pattern Mapping**
   - Map live merge input paths
   - Identify legacy compatibility usage
   - Document current call sites

3. **Dependency Graph**
   - Create visual dependency map
   - Identify critical vs optional dependencies

### Phase 2: Design (2 days)
1. **Separation Strategy**
   - Option A: Extract live code to new module
   - Option B: In-place separation with clear boundaries
   - Option C: Full rewrite with clean interface

2. **Create ADR**
   - `ADR-047-merge-input-mixin-separation.md`
   - Document separation rationale
   - Define migration path

### Phase 3: Implementation (3 days)
1. **Separate Live from Legacy**
   ```python
   # Example separated structure
   class LiveMergeInputLoader:
       """Modern merge input loader (Gold layer)."""
       
       def load_input(self, context: MergeContext) -> MergeInput:
           # Clean implementation
           return self._load_from_gold_layer(context)
   
   class LegacyMergeInputAdapter:
       """Legacy silver layer adapter (deprecated)."""
       
       def adapt_silver_input(self, silver_data: SilverData) -> GoldCompatibleInput:
           # Legacy compatibility
           return self._transform_to_gold_format(silver_data)
   ```

2. **Update Call Sites**
   - Migrate live paths to new interface
   - Deprecate legacy paths
   - Add clear documentation

3. **Improve Testing**
   - Separate tests for live vs legacy
   - Achieve ≥90% coverage for live code
   - Document legacy code as deprecated

### Phase 4: Validation (1 day)
1. **Test Separation**
   ```bash
   # Run merge tests
   pytest tests/application/composite/ -k "merge" -v
   ```

2. **Verify No Regressions**
   - Compare merge behavior
   - Check performance
   - Validate data integrity

3. **Documentation Update**
   - Update merge architecture docs
   - Add deprecation notices
   - Document migration path

## Success Criteria

- [ ] Live merge input paths clearly separated
- [ ] Legacy compatibility marked for deprecation
- [ ] Test coverage ≥90% for live code
- [ ] No regressions in merge functionality
- [ ] Clear migration path documented

## Verification Commands

```bash
# Check for mixed concerns
grep -rn "silver\|legacy" src/bioetl/application/composite/merger_input_mixin.py

# Run merge tests
pytest tests/application/composite/test_merger* -v

# Type checking
mypy src/bioetl/application/composite/merger_input_mixin.py --strict

# Coverage
pytest --cov=src/bioetl/application/composite/merger_input_mixin.py --cov-report=term
```

## Impact Assessment

**Positive Impacts:**
- Clearer merge architecture
- Easier testing and maintenance
- Reduced cognitive load
- Better separation of concerns

**Potential Risks:**
- Merge behavior changes
- Legacy compatibility issues
- Performance impact

**Mitigation:**
- Comprehensive testing
- Gradual deprecation
- Clear documentation

## Related Issues

- Related: TD-04 (checkpoint state) - similar separation pattern
- Blocks: TD-06 (zero-anchor audit) - validate signals

## Checklist

- [ ] Separation analysis complete
- [ ] ADR created and approved
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Documentation updated

## Time Estimate

**Total**: 8 days  
**Start**: 2024-04-28  
**Target Completion**: 2024-05-09

## Assignee

(TBD - comment on tracking issue to claim)

## Decision Points

1. **Separation vs Rewrite**: Extract vs clean rewrite
2. **Deprecation Timeline**: Gradual vs immediate
3. **Legacy Support**: How long to maintain compatibility

## Notes

This issue represents an opportunity to clean up the merge architecture and establish clearer patterns for future development. The separation will make it easier to eventually remove legacy silver layer compatibility.
