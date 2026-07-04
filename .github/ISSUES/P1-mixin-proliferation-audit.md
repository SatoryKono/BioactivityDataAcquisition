---
title: "[P1] Audit and consolidate mixin proliferation (154 files)"
labels: priority/P1, technical-debt, architecture, enhancement
assignees: []
---

## Context

Technical debt audit identified **154 files with mixin classes** across the codebase, representing potential architectural debt. Mixins enable flexible composition but increase cognitive load and can hide dependencies.

## Current State

- **Domain Layer**: ~20 mixin files
- **Application Layer**: 50+ mixin files
- **Infrastructure Layer**: 40+ mixin files
- **Interfaces Layer**: ~10 mixin files (including HTTP mixins)

## Problem

1. **Cognitive complexity**: Mixins make flow difficult to understand and debug
2. **Hidden dependencies**: Mixin dependencies are not explicit in type signatures
3. **Maintenance burden**: Changes to mixins can have wide-ranging, unexpected effects
4. **No governance**: No policy exists for creating new mixins

## Impact

- **Risk**: Medium - hidden dependencies and complexity
- **Effort**: High - requires systematic audit and refactoring

## Proposed Solution

### Phase 1: Inventory (Week 1)
1. Create detailed mixin inventory with classification:
   - Observability mixins
   - Storage mixins (bronze/silver metadata)
   - Application logic mixins
   - HTTP/transport mixins
2. Map mixin usage patterns and dependencies
3. Identify critical consolidation opportunities

### Phase 2: Consolidation (Week 2-4)
1. Start with low-risk storage mixins (bronze/silver metadata)
2. Consolidate observable duplicates in application layer
3. Replace mixins with explicit composition where appropriate
4. Document remaining mixins with justification

### Phase 3: Governance (Week 5)
1. Add mixin governance policy to `AGENTS.md` or `docs/00-project/RULES.md`
2. Require justification for new mixins in PR reviews
3. Add architecture test to detect mixin complexity violations

## Acceptance Criteria

- [ ] Detailed mixin inventory created and documented
- [ ] At least 20% of mixins consolidated or replaced with explicit composition
- [ ] Mixin governance policy added to project rules
- [ ] Architecture test added for mixin complexity
- [ ] No regression in functionality
- [ ] All tests pass

## Related Files

- Mixin files across `src/bioetl/domain/`, `src/bioetl/application/`, `src/bioetl/infrastructure/`
- `docs/00-project/RULES.md` (for governance policy)
- `AGENTS.md` (for architecture test guidance)

## References

- Technical Debt Audit: Mixin proliferation analysis
- ADR-026: Composite Pipeline Pattern (may provide guidance on composition alternatives)

## Notes

This is **P1 priority** due to the scale (154 files) and architectural impact. Start with low-risk storage mixins before tackling application logic mixins.