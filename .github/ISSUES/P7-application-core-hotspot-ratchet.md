---
title: "[P7] Continue hotspot ratchet for application/core/ (174 files, 21611 LOC)"
labels: priority/P7, technical-debt, hotspot, enhancement
assignees: []
---

## Context

Technical debt audit identified `application/core/` as a **hotspot** with **174 files and 21,611 LOC**. While growth is bounded by budgets in `debt_scorecard.yaml`, continued ratchet is needed per RF-023.

## Current State

- **Path**: `src/bioetl/application/core/`
- **Files**: 174
- **LOC**: 21,611
- **Growth control**: Bounded by budgets in `debt_scorecard.yaml`
- **Ratchet status**: Per RF-023, continued reduction needed

## Problem

1. **Complexity concentration**: Core orchestration logic is becoming complex
2. **Maintenance burden**: Large module is difficult to navigate and understand
3. **Refactoring risk**: Changes have wide-ranging impact
4. **Bounded but growing**: Even with budgets, absolute size continues to increase

## Impact

- **Risk**: Medium - hotspot represents single point of complexity
- **Effort**: High - requires systematic refactoring and extraction

## Proposed Solution

### Phase 1: Analysis (Week 1-2)
1. Analyze `application/core/` structure:
   - Identify natural sub-module boundaries
   - Map dependencies between components
   - Identify extraction opportunities
   - Assess coupling and cohesion
2. Review current budget utilization in `debt_scorecard.yaml`
3. Identify low-hanging fruit for extraction

### Phase 2: Extraction Planning (Week 2-3)
1. Plan extraction of cohesive sub-modules:
   - Identify candidate sub-modules (e.g., lifecycle, orchestration, coordination)
   - Define sub-module boundaries and responsibilities
   - Plan dependency inversion for extracted modules
   - Assess migration risk per sub-module

### Phase 3: Incremental Extraction (Week 4-8)
1. Extract low-risk sub-modules incrementally:
   - Start with least coupled components
   - Maintain backward compatibility during migration
   - Update imports and references
   - Verify no functionality regression
2. Update `debt_scorecard.yaml` budgets as extraction progresses
3. Document new module structure

### Phase 4: Validation (Week 8-9)
1. Validate extraction results:
   - Measure complexity reduction
   - Verify improved navigability
   - Assess test coverage
   - Update architecture documentation

## Acceptance Criteria

- [ ] Core structure analysis completed with extraction plan
- [ ] At least 2 sub-modules extracted from `application/core/`
- [ ] LOC reduced by at least 10% (to ~19,450 LOC)
- [ ] File count reduced by at least 10% (to ~156 files)
- [ ] `debt_scorecard.yaml` budgets updated
- [ ] Architecture documentation updated
- [ ] No regression in functionality
- [ ] All tests pass

## Related Files

- `src/bioetl/application/core/` (174 files, 21,611 LOC)
- `configs/quality/debt_scorecard.yaml` (budgets)
- RF-023 (hotspot ratchet requirements)

## References

- Technical Debt Audit: Hotspot management analysis
- RF-023: Hotspot ratchet requirements
- Debt Scorecard governance

## Notes

This is **P7 priority** because growth is bounded by budgets and controlled. The goal is incremental reduction through extraction, not aggressive refactoring. Focus on natural sub-module boundaries and low-risk extractions. Coordinate with debt scorecard quarterly review cycle.