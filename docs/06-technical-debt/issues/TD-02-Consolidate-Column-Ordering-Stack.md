# TD-02: Consolidate or Retire Column Ordering Stack

**Status**: Open  
**Priority**: P0  
**Labels**: `technical-debt`, `refactoring`, `composite-layer`, `cleanup`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

The column ordering stack contains multiple overlapping and potentially redundant components:
- `column_orderer.py`
- `column_priority_orderer.py`
- `ColumnOrderer` class
- `ColumnPriorityOrderer` class
- `collect_priority_field_columns` function

These entities appear in both retirement_candidate and complexity_candidate lists, making them strong candidates for consolidation or removal.

## Root Cause

Historical evolution without clear ownership boundaries has led to:
- Overlapping functionality
- Inconsistent APIs
- Confusing naming conventions
- Maintenance burden

## Scope

**Affected Files:**
```bash
find src/bioetl/application/composite/ -name "*column*" -type f
# Expected output:
# src/bioetl/application/composite/column_orderer.py
# src/bioetl/application/composite/column_orderer_group_flow.py
# src/bioetl/application/composite/column_orderer_semantic.py
# src/bioetl/application/composite/column_priority_orderer.py
# src/bioetl/application/composite/column_renamer.py
```

**Impact Analysis:**
```bash
# Find usages
grep -r "ColumnOrderer\|ColumnPriorityOrderer\|collect_priority_field_columns" src/ --include="*.py" | wc -l
```

## Solution Plan

### Phase 1: Analysis (3 days)
1. **Map current usage**
   ```bash
   # Create usage map
   grep -rn "from.*column_orderer\|import.*ColumnOrderer" src/ > reports/column_usage_map.txt
   ```

2. **Identify live vs dead code paths**
   - Check test coverage
   - Analyze git history
   - Consult with domain experts

3. **Determine consolidation strategy**
   - Option A: Unify into single ColumnOrderer
   - Option B: Deprecate entire stack in favor of new approach
   - Option C: Keep minimal viable subset

### Phase 2: Decision & Design (2 days)
1. **Create Architecture Decision Record**
   - Document rationale in `docs/02-architecture/decisions/ADR-044-column-ordering-consolidation.md`
   - Include usage analysis
   - Define migration path

2. **Design unified interface**
   ```python
   # Proposed unified interface
   class ColumnOrderService:
       """Unified column ordering service."""
       
       def __init__(self, strategy: ColumnOrderStrategy = ColumnOrderStrategy.PRIORITY):
           self._strategy = strategy
           
       def order_columns(self, dataframe: pd.DataFrame, schema: ColumnSchema) -> pd.DataFrame:
           """Order columns according to strategy."""
           # Unified implementation
           
       def collect_priority_columns(self, schema: ColumnSchema) -> list[str]:
           """Collect priority columns from schema."""
           # Single implementation
   ```

### Phase 3: Implementation (4 days)
1. **Create unified service**
   - Implement in `src/bioetl/application/composite/column_service.py`
   - Add comprehensive tests
   - Ensure backward compatibility

2. **Migrate existing code**
   - Replace old imports with new service
   - Update call sites
   - Preserve behavior

3. **Deprecate old components**
   - Add deprecation warnings
   - Mark for removal in next major version
   - Update documentation

### Phase 4: Validation (2 days)
1. **Test migration**
   ```bash
   # Run affected tests
   pytest tests/application/composite/test_column* -v
   ```

2. **Verify no regressions**
   - Compare column ordering results
   - Check performance
   - Validate schema compliance

3. **Update documentation**
   - Composite layer documentation
   - Migration guide
   - API reference

## Success Criteria

- [ ] Column ordering complexity reduced by ≥60%
- [ ] Single unified interface for column operations
- [ ] All existing functionality preserved
- [ ] Test coverage ≥95%
- [ ] No breaking changes in current version
- [ ] Clear deprecation path established

## Verification Commands

```bash
# Check import usage
grep -rn "from.*column_orderer\|from.*column_priority" src/ | grep -v "column_service"

# Run tests
pytest tests/application/composite/ -k "column" -v

# Type checking
mypy src/bioetl/application/composite/column_service.py --strict

# Coverage report
pytest --cov=src/bioetl/application/composite/column_service.py --cov-report=term
```

## Impact Assessment

**Positive Impacts:**
- Reduced cognitive load for developers
- Consistent column ordering behavior
- Easier testing and maintenance
- Clearer API surface

**Potential Risks:**
- Behavior changes in edge cases
- Performance impact
- Migration complexity

**Mitigation:**
- Comprehensive test suite
- Gradual migration
- Feature flags if needed

## Related Issues

- Related: TD-01 (duplication cluster) - similar consolidation pattern
- Blocks: TD-08 (scoring calibration) - validate retirement signals

## Checklist

- [ ] Usage analysis complete
- [ ] ADR created and approved
- [ ] Unified service implemented
- [ ] Migration complete
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Deprecation warnings added

## Time Estimate

**Total**: 11 days  
**Start**: 2024-04-15  
**Target Completion**: 2024-05-01

## Assignee

(TBD - comment on tracking issue to claim)

## Decision Points

1. **Consolidation vs Removal**: Need to decide whether to unify or remove entirely
2. **Backward Compatibility**: How to handle breaking changes
3. **Migration Timeline**: Gradual vs immediate deprecation

## Notes

This issue represents a significant opportunity to reduce complexity in the composite layer. The column ordering stack has been a persistent source of confusion and should be simplified before adding new features.
