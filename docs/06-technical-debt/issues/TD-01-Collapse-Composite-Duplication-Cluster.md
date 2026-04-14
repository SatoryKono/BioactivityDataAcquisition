# TD-01: Collapse Composite Duplication Cluster 8b680b57b0a1

**Status**: Open  
**Priority**: P0  
**Labels**: `technical-debt`, `refactoring`, `composite-layer`, `duplication`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

Composite duplication cluster `8b680b57b0a1` contains **78 duplicate instances** across the codebase. This is not a local code smell but a systemic pattern indicating a missing abstraction.

## Root Cause

Multiple composite helpers are copying the same method-level flow instead of extracting a common behavior seam. This violates DRY principles and increases maintenance burden.

## Scope

**Affected Areas:**
- `src/bioetl/application/composite/` - Primary location
- `src/bioetl/application/services/` - Secondary impact
- Test files that depend on these composites

**Files to Investigate:**
```bash
# Find files with potential duplication
find src/bioetl/application/composite/ -name "*.py" -exec grep -l "8b680b57b0a1\|duplicate.*composite\|composite.*helper" {} \;
```

## Solution Plan

### Phase 1: Analysis (2 days)
1. **Identify exact duplication locations**
   ```bash
   # Use jscpd or similar duplication detector
   jscpd --format python --output reports/duplication/ src/bioetl/application/composite/
   ```

2. **Extract common behavior seam**
   - Analyze the 78 instances to find the core pattern
   - Document the common workflow
   - Identify variation points

3. **Design sanctioned composite helper**
   - Create `src/bioetl/application/composite/helpers/common_behavior.py`
   - Define clear interface with extension points
   - Ensure type safety with Protocol

### Phase 2: Implementation (5 days)
1. **Create the helper**
   ```python
   # Example structure
   class CompositeBehaviorHelper:
       """Sanctioned helper for common composite patterns."""
       
       def __init__(self, variation_config: VariationConfig):
           self._config = variation_config
           
       def execute_common_flow(self, context: CompositeContext) -> CompositeResult:
           # Common logic here
           result = self._execute_core_logic(context)
           return self._apply_variations(result)
   ```

2. **Refactor duplicates to use helper**
   - Replace duplicate code with helper calls
   - Preserve existing behavior
   - Update type annotations

3. **Update tests**
   - Modify existing tests to use helper
   - Add new tests for helper itself
   - Ensure 100% coverage of helper

### Phase 3: Validation (2 days)
1. **Run full test suite**
   ```bash
   pytest tests/ -x -v --tb=short
   ```

2. **Verify no regressions**
   - Compare before/after behavior
   - Check performance metrics
   - Validate import boundaries

3. **Update documentation**
   - Add helper to composite layer docs
   - Update architecture decisions
   - Add usage examples

## Success Criteria

- [ ] 78 duplicate instances reduced to ≤5
- [ ] Common helper created and documented
- [ ] All existing tests pass
- [ ] New helper has ≥95% test coverage
- [ ] No architecture boundary violations
- [ ] Performance maintained or improved

## Verification Commands

```bash
# Check for remaining duplicates
jscpd --format python --threshold 5 --output reports/duplication-final/ src/bioetl/application/composite/

# Run architecture tests
pytest tests/architecture/ -v

# Type checking
mypy src/bioetl/application/composite/ --strict

# Test coverage
pytest --cov=src/bioetl/application/composite/ --cov-report=term
```

## Impact Assessment

**Positive Impacts:**
- Reduced codebase size by ~1,200 lines
- Improved maintainability
- Faster onboarding
- Reduced bug surface area

**Potential Risks:**
- Behavior changes if variation points not properly identified
- Performance impact if helper adds overhead
- Test coverage gaps

**Mitigation:**
- Comprehensive testing
- Performance benchmarking
- Gradual rollout

## Related Issues

- Blocks: TD-08 (calibration improvements)
- Related: TD-02 (column ordering consolidation)

## Checklist

- [ ] Duplication analysis complete
- [ ] Helper design approved
- [ ] Implementation complete
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Performance validated
- [ ] Architecture review passed

## Time Estimate

**Total**: 9 days  
**Start**: 2024-04-15  
**Target Completion**: 2024-04-29

## Assignee

(TBD - comment on tracking issue to claim)

## Notes

This issue represents the largest duplication cluster in the codebase. Success here will significantly improve the composite layer's maintainability and set a pattern for future refactoring.
