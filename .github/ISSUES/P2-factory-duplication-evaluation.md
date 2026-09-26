---
title: "[P2] Evaluate and consolidate factory class duplication (24 classes)"
labels: priority/P2, technical-debt, duplication, enhancement
assignees: []
---

## Context

Technical debt audit identified **24 Factory classes** with potential duplication of assembly logic across the codebase. Separate factories ensure testability and DI, but may contain duplicate logic.

## Current State

- 24 Factory classes identified across composition layer
- Potential duplication in pipeline assembly logic
- No systematic mapping of factory dependencies

## Problem

1. **Duplication risk**: Similar assembly logic may be duplicated across factories
2. **Synchronization risk**: Changes to common patterns may miss some factories
3. **Maintenance burden**: Understanding factory relationships requires manual tracing
4. **No detection**: No architecture test to detect factory pattern violations

## Impact

- **Risk**: Medium - potential for inconsistent behavior across factories
- **Effort**: Medium - dependency analysis and targeted refactoring

## Proposed Solution

### Phase 1: Mapping (Week 1)
1. Build dependency graph for all 24 Factory classes
2. Identify common assembly patterns and duplication
3. Map factory-to-pipeline relationships
4. Document factory responsibilities

### Phase 2: Analysis (Week 2)
1. Evaluate which duplication is legitimate (DI requirements) vs. actual debt
2. Identify opportunities for base class extraction
3. Identify opportunities for helper functions
4. Assess consolidation feasibility per factory

### Phase 3: Refactoring (Week 3-4)
1. Extract common logic to base classes or helpers
2. Document remaining duplication with justification
3. Add architecture test for factory pattern compliance
4. Update factory documentation

## Acceptance Criteria

- [ ] Factory dependency graph created and documented
- [ ] Duplication analysis completed with classification
- [ ] At least 30% of duplications consolidated or justified
- [ ] Architecture test added for factory pattern compliance
- [ ] Factory documentation updated
- [ ] No regression in functionality
- [ ] All tests pass

## Related Files

- Factory classes in `src/bioetl/composition/factories/`
- `src/bioetl/composition/factories/pipeline/`
- `src/bioetl/composition/factories/adapter/`

## References

- Technical Debt Audit: Factory duplication analysis
- ADR-026: Composite Pipeline Pattern

## Notes

This is **P2 priority** because some duplication is legitimate for DI/testability. Focus on identifying and consolidating actual debt, not legitimate separation of concerns.