---
title: "[P4] Resolve TEMPORAL TODO marker in publication_fields.py:260"
labels: priority/P4, technical-debt, code-quality, bug
assignees: []
---

## Context

Technical debt audit identified **1 TEMPORAL TODO marker** in production code at `src/bioetl/domain/mapping/publication_fields.py:260`. TEMPORAL markers should be resolved or documented with explicit timeline.

## Current State

- **File**: `src/bioetl/domain/mapping/publication_fields.py`
- **Line**: 260
- **Marker**: TEMPORAL TODO
- **Impact**: Production code with temporary marker

## Problem

1. **Technical debt indicator**: TEMPORAL markers indicate incomplete implementation
2. **No timeline**: No documented resolution timeline or owner
3. **Production risk**: Temporary code in production may have edge cases
4. **Governance gap**: No automated detection of TEMPORAL markers in production code

## Impact

- **Risk**: Low - single marker, likely low impact
- **Effort**: Low - localized fix

## Proposed Solution

### Investigation (Day 1)
1. Read the TODO marker at line 260
2. Understand the context and reason for TEMPORARY designation
3. Assess if the temporary code is still needed
4. Identify if the temporary implementation can be made permanent or removed

### Resolution (Day 1-2)
1. **If temporary code is no longer needed**: Remove and implement proper solution
2. **If temporary code is still needed**: Document with explicit timeline and owner
3. **If temporary code should be permanent**: Remove TEMPORAL marker and add proper documentation
4. Add architecture test to detect new TEMPORAL markers in production code

## Acceptance Criteria

- [ ] TEMPORAL marker resolved (removed or documented with timeline)
- [ ] Code implementation is production-ready
- [ ] Architecture test added to detect TEMPORAL markers in production code
- [ ] No regression in functionality
- [ ] All tests pass

## Related Files

- `src/bioetl/domain/mapping/publication_fields.py:260`

## References

- Technical Debt Audit: TODO debt analysis

## Notes

This is **P4 priority** because it's a single marker with likely low impact. Quick win that also adds governance (architecture test) to prevent future TEMPORAL marker accumulation.