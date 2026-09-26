---
title: "[P8] Continue hotspot ratchet for bootstrap/runtime/ (44 files, 5758 LOC)"
labels: priority/P8, technical-debt, hotspot, enhancement
assignees: []
---

## Context

Technical debt audit identified `bootstrap/runtime/` as a **hotspot** with **44 files and 5,758 LOC**. While growth is bounded by budgets in `debt_scorecard.yaml`, continued ratchet is needed per RF-023.

## Current State

- **Path**: `src/bioetl/composition/bootstrap/runtime/`
- **Files**: 44
- **LOC**: 5,758
- **Growth control**: Bounded by budgets in `debt_scorecard.yaml`
- **Ratchet status**: Per RF-023, continued reduction needed

## Problem

1. **Bootstrap complexity**: Runtime bootstrap is becoming complex
2. **Dependency injection**: Many bootstrap functions may have overlapping responsibilities
3. **Registration logic**: Pipeline and provider registration may have duplication
4. **Bounded but growing**: Even with budgets, absolute size continues to increase

## Impact

- **Risk**: Medium - bootstrap complexity affects application startup
- **Effort**: Medium - smaller than application/core/, but requires careful refactoring

## Proposed Solution

### Phase 1: Analysis (Week 1)
1. Analyze `bootstrap/runtime/` structure:
   - Map bootstrap function responsibilities
   - Identify overlapping registration logic
   - Assess duplication between provider and pipeline registration
   - Identify consolidation opportunities
2. Review current budget utilization in `debt_scorecard.yaml`
3. Identify low-hanging fruit for consolidation

### Phase 2: Consolidation Planning (Week 1-2)
1. Plan consolidation of bootstrap logic:
   - Identify common registration patterns
   - Plan extraction of shared utilities
   - Assess consolidation risk per function
   - Define consolidated bootstrap flow

### Phase 3: Incremental Consolidation (Week 2-4)
1. Consolidate bootstrap functions incrementally:
   - Extract shared registration utilities
   - Consolidate overlapping provider registration
   - Simplify pipeline registration flow
   - Maintain backward compatibility during migration
2. Update `debt_scorecard.yaml` budgets as consolidation progresses
3. Document bootstrap architecture

### Phase 4: Validation (Week 4-5)
1. Validate consolidation results:
   - Measure complexity reduction
   - Verify improved bootstrap clarity
   - Assess test coverage
   - Update architecture documentation

## Acceptance Criteria

- [ ] Bootstrap structure analysis completed with consolidation plan
- [ ] At least 3 shared registration utilities extracted
- [ ] LOC reduced by at least 15% (to ~4,894 LOC)
- [ ] File count reduced by at least 10% (to ~40 files)
- [ ] `debt_scorecard.yaml` budgets updated
- [ ] Bootstrap architecture documented
- [ ] No regression in functionality
- [ ] All tests pass

## Related Files

- `src/bioetl/composition/bootstrap/runtime/` (44 files, 5,758 LOC)
- `configs/quality/debt_scorecard.yaml` (budgets)
- RF-023 (hotspot ratchet requirements)

## References

- Technical Debt Audit: Hotspot management analysis
- RF-023: Hotspot ratchet requirements
- Debt Scorecard governance

## Notes

This is **P8 priority** because the hotspot is smaller than `application/core/` and growth is well-controlled. The goal is consolidation and simplification rather than aggressive extraction. Focus on shared utilities and registration logic duplication. Coordinate with debt scorecard quarterly review cycle.