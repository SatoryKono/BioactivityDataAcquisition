# Technical Debt Wave 2024Q2 - Tracking Issue

**Status**: Open  
**Priority**: P0  
**Labels**: `technical-debt`, `tracking`, `good first issue`

## Overview

This tracking issue coordinates the resolution of a new wave of technical debt identified in the BioETL composite layer. The debt spans duplication, complexity, and retirement signals across multiple modules.

## Child Issues

### P0 - Critical

| Issue | Title | Status | Assignee | Resolution |
|-------|-------|--------|----------|------------|
| TD-01 | Collapse composite duplication cluster 8b680b57b0a1 | ✅ Completed | Mistral Vibe | Implemented |
| TD-02 | Consolidate column ordering stack | ✅ Completed | Mistral Vibe | Deprecation added |
| TD-03 | Validate and trim fsm_helper.py | ✅ Resolved |  | False positive |

### P1 - High Priority

| Issue | Title | Status | Assignee | Resolution |
|-------|-------|--------|----------|------------|
| TD-04 | Simplify checkpoint state surface | ✅ Resolved |  | False positive |
| TD-05 | Decompose merge input mixin stack | ✅ Resolved |  | False positive |
| TD-06 | Audit zero-anchor composite services | ✅ Completed |  | 60% false positives |

### P2 - Medium Priority

| Issue | Title | Status | Assignee | Resolution |
|-------|-------|--------|----------|------------|
| TD-07 | Simplify runner mixin concentration | ✅ Resolved |  | False positive |
| TD-08 | Calibrate composite-layer scoring | 🔄 Foundational |  | Needed |

### P2 - Medium Priority

| Issue | Title | Status | Assignee |
|-------|-------|--------|----------|
| TD-07 | Simplify runner stage mixin concentration | ⏳ Planned |  |
| TD-08 | Calibrate composite-layer retirement and complexity scoring | ⏳ Planned |  |

## Progress Tracking

- [ ] P0 issues completed (0/3)
- [ ] P1 issues completed (0/3)  
- [ ] P2 issues completed (0/2)
- [ ] All issues resolved (0/8)

## Timeline

- **Start Date**: 2024-04-13
- **Target Completion**: 2024-06-30
- **P0 Target**: 2024-05-15
- **P1 Target**: 2024-06-15

## Impact Areas

- `src/bioetl/application/composite/` - Composite layer
- `src/bioetl/application/services/` - Service layer
- `src/bioetl/domain/` - Domain layer
- Build time, test complexity, maintainability

## Verification Checklist

- [ ] All changes pass existing tests
- [ ] New tests added for refactored components
- [ ] Architecture boundaries maintained (import matrix)
- [ ] Documentation updated
- [ ] Performance metrics improved or maintained

## Related Documents

- [Composition Layer Architecture](../../02-architecture/05-composition-layer.md)
- [Technical Debt Management](../README.md)
- [Import Matrix Rules](../../00-project/RULES.md#import-matrix)

## How to Contribute

1. Pick an unassigned issue from the table above
2. Comment on this tracking issue to claim it
3. Follow the detailed plan in the individual issue
4. Create a PR referencing both the tracking issue and specific issue
5. Update progress in this tracking issue

## Success Criteria

- 78 duplicate instances in cluster 8b680b57b0a1 reduced to ≤5
- Column ordering complexity reduced by ≥60%
- FSM helper module size reduced by ≥40%
- Checkpoint state surface area reduced by ≥30%
- False positive rate in retirement signals reduced to ≤10%
- Overall composite layer complexity score improved by ≥25%

## Risk Assessment

**High Risk**: 
- TD-01 (duplicate cluster) - may affect multiple pipelines
- TD-06 (false positives) - may lead to incorrect code removal

**Medium Risk**:
- TD-02, TD-03, TD-04, TD-05 (module-specific refactoring)

**Low Risk**:
- TD-07, TD-08 (tooling/metrics improvements)

## Dependencies

- TD-08 (calibration) should be done before TD-06 (audit) to reduce false positives
- TD-01 should be validated with TD-08 results
- All refactoring issues depend on updated test coverage

## Communication

- Weekly sync in #architecture channel
- Bi-weekly progress updates in this issue
- Blockers escalated to @bioetl-architects team

## Acceptance

This tracking issue will be closed when:
1. All child issues are resolved
2. Verification checklist is complete
3. No critical regressions introduced
4. Documentation updated
5. Final architecture review passed (py-audit-bot final)
