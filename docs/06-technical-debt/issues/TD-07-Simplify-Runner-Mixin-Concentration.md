# TD-07: Simplify Runner Stage Mixin Concentration

**Status**: Open  
**Priority**: P2  
**Labels**: `technical-debt`, `refactoring`, `runner`, `mixin`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

The runner package contains a concentration of mixins that form a hotspot:
- `CompositeRunnerMergeStageMixin`
- `_get_explicit_merger_method`
- `CompositeRunnerStageMixin`
- `_CompositeRunnerStageEnrichmentMixin`

This concentration suggests:
- Overuse of mixin pattern
- Potential for simplification
- Future technical debt target

## Root Cause

Historical growth of runner architecture has led to:
- Accumulation of stage-specific mixins
- Complex inheritance hierarchies
- Difficulty in understanding execution flow
- Testing challenges

## Scope

**Primary Files:**
- `src/bioetl/application/composite/runner/*.py`
- Related runner service files

**Impact Analysis:**
```bash
# Find runner mixin usage
grep -rn "CompositeRunner.*Mixin" src/ --include="*.py"

# Check complexityadon cc src/bioetl/application/composite/runner/ -a
```

## Solution Plan

### Phase 1: Analysis (2 days)
1. **Mixin Usage Mapping**
   ```bash
   # Create mixin dependency graph
   grep -rn "class.*Mixin" src/bioetl/application/composite/runner/ > reports/runner_mixin_map.txt
   ```

2. **Pattern Identification**
   - Identify common mixin patterns
   - Document inheritance hierarchies
   - Find simplification opportunities

3. **Impact Assessment**
   - Estimate refactoring effort
   - Identify risk areas
   - Determine priority

### Phase 2: Design (1 day)
1. **Simplification Strategy**
   - Consolidate related mixins
   - Reduce inheritance depth
   - Clarify responsibilities

2. **Create Improvement Plan**
   - Document in `reports/technical-debt/runner-simplification-plan.md`
   - Prioritize changes
   - Define success metrics

### Phase 3: Implementation (2 days)
1. **Consolidate Mixins**
   ```python
   # Example consolidated mixin
   class CompositeRunnerStageMixin:
       """Consolidated stage mixin with clear responsibilities."""
       
       def execute_stage(self, stage_config: StageConfig) -> StageResult:
           """Execute a single stage."""
           if stage_config.stage_type == StageType.MERGE:
               return self._execute_merge_stage(stage_config)
           elif stage_config.stage_type == StageType.ENRICHMENT:
               return self._execute_enrichment_stage(stage_config)
   ```

2. **Reduce Inheritance Complexity**
   - Flatten inheritance hierarchies
   - Use composition over inheritance where appropriate
   - Improve type safety

3. **Update Tests**
   - Modify existing tests
   - Add new test cases
   - Ensure coverage ≥90%

### Phase 4: Validation (1 day)
1. **Test Refactoring**
   ```bash
   # Run runner tests
   pytest tests/application/composite/runner/ -v
   ```

2. **Performance Validation**
   - Compare before/after performance
   - Check memory usage
   - Validate execution flow

3. **Documentation Update**
   - Update runner architecture docs
   - Add usage examples
   - Document simplification rationale

## Success Criteria

- [ ] Runner mixin complexity reduced by ≥30%
- [ ] Inheritance depth reduced
- [ ] Clearer responsibilities
- [ ] Test coverage ≥90%
- [ ] No regressions in runner functionality

## Verification Commands

```bash
# Check remaining complexityadon cc src/bioetl/application/composite/runner/ -a

# Run runner tests
pytest tests/application/composite/runner/ -v --tb=short

# Type checking
mypy src/bioetl/application/composite/runner/ --strict

# Coverage
pytest --cov=src/bioetl/application/composite/runner/ --cov-report=term
```

## Impact Assessment

**Positive Impacts:**
- Simplified runner architecture
- Easier testing and maintenance
- Reduced cognitive load
- Better performance

**Potential Risks:**
- Runner behavior changes
- Performance impact
- Testing gaps

**Mitigation:**
- Comprehensive testing
- Performance benchmarking
- Gradual refactoring

## Related Issues

- Related: TD-01 (duplication) - similar consolidation pattern
- Blocks: TD-08 (scoring) - validate as future target

## Checklist

- [ ] Analysis complete
- [ ] Simplification plan created
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Documentation updated

## Time Estimate

**Total**: 6 days  
**Start**: 2024-05-16  
**Target Completion**: 2024-05-24

## Assignee

(TBD - comment on tracking issue to claim)

## Future Work

This issue identifies the runner mixin concentration as a future simplification target. The work done here will:
- Reduce future technical debt accumulation
- Establish better patterns for runner development
- Improve maintainability of execution flow

## Notes

This is identified as a "concentration hotspot" and "next крупный simplification target" in the original debt analysis. Addressing this will prevent future complexity growth in the runner layer.
