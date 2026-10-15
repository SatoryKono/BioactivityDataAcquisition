---
title: "[P3] Reduce first-party imports for domain/composite/config.py (81 importers)"
labels: priority/P3, technical-debt, compatibility, enhancement
assignees: []
---

## Context

Technical debt audit identified that `domain/composite/config.py` has **81 first-party importers**, making it a high-traffic compatibility facade. While this is a stable public API, reducing direct first-party imports through targeted facades would improve modularity.

## Current State

- **Path**: `src/bioetl/domain/composite/config.py`
- **First-party importers**: 81 src files
- **Test importers**: 34 test files
- **Status**: Stable public API, managed in `compatibility_facade_inventory.yaml`

## Problem

1. **High coupling**: 81 first-party importers create tight coupling to composite config
2. **Modularity**: Direct imports bypass potential abstraction layers
3. **Refactoring risk**: Changes to composite config affect many files
4. **Facade narrowing**: Opportunity to create more targeted facades

## Impact

- **Risk**: Low - stable API, well-governed
- **Effort**: Medium - requires identifying usage patterns and creating targeted facades

## Proposed Solution

### Phase 1: Analysis (Week 1)
1. Analyze the 81 first-party importers:
   - What specific symbols they import from composite config
   - Usage patterns (type hints vs. runtime usage)
   - Grouping by functional area
2. Identify natural facade boundaries
3. Assess which imports could be redirected to more specific modules

### Phase 2: Facade Design (Week 2)
1. Design targeted facades for common import patterns
2. Identify which imports should remain direct (legitimate use cases)
3. Plan migration path with minimal disruption
4. Document facade responsibilities

### Phase 3: Migration (Week 3-4)
1. Create new targeted facades
2. Migrate importers incrementally
3. Update documentation
4. Verify no functionality regression

## Acceptance Criteria

- [ ] Importer analysis completed with usage pattern classification
- [ ] Targeted facade design documented
- [ ] At least 30% of first-party importers migrated to targeted facades
- [ ] Documentation updated
- [ ] No regression in functionality
- [ ] All tests pass
- [ ] `compatibility_facade_inventory.yaml` updated if new facades added

## Related Files

- `src/bioetl/domain/composite/config.py`
- `configs/quality/compatibility_facade_inventory.yaml`
- Importer files (81 first-party importers identified in audit)

## References

- Technical Debt Audit: Compatibility debt analysis
- Compatibility Facade Inventory governance

## Notes

This is **P3 priority** because the current state is well-governed and functional. The goal is incremental improvement through targeted facades, not a complete refactor. Focus on high-impact, low-risk opportunities.