# TD-06: Audit Zero-Anchor Composite Services for False Positives

**Status**: Open  
**Priority**: P1  
**Labels**: `technical-debt`, `audit`, `false-positives`, `metrics`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

Multiple composite services (MergeService, EnricherDeduplicatorService) show:
- High retirement scores
- Zero anchors in composite-layer
- Potential false positive signals

This suggests either:
1. Genuinely orphaned orchestration code
2. Underscored live dependencies
3. Graph signal accuracy issues

## Root Cause

Current retirement/complexity scoring may have:
- Incomplete dependency detection
- Overly aggressive anchor requirements
- Missing composite-layer context
- False assumptions about service lifecycles

## Scope

**Services to Audit:**
- `MergeService`
- `EnricherDeduplicatorService`
- Other services with deletion_score=8 and 0/0/0/0 anchors

**Impact Analysis:**
```bash
# Find zero-anchor services
grep -rn "class.*Service" src/bioetl/application/services/ | xargs -I {} sh -c 'echo "Checking {}"; grep -rn "{}" src/ --include="*.py" | wc -l'
```

## Solution Plan

### Phase 1: Signal Validation (3 days)
1. **Manual Code Review**
   - Examine each flagged service
   - Determine actual usage patterns
   - Document findings

2. **Dependency Graph Analysis**
   ```bash
   # Create dependency map
   pydeps src/bioetl/application/services/ --show-dot | dot -Tsvg > reports/service_dependencies.svg
   ```

3. **Test Coverage Correlation**
   - Check if services are tested
   - Identify test gaps
   - Correlate with usage signals

### Phase 2: False Positive Identification (2 days)
1. **Pattern Recognition**
   - Identify common false positive patterns
   - Document signal limitations
   - Create false positive catalog

2. **Create Audit Report**
   - `reports/technical-debt/zero-anchor-audit-2024Q2.md`
   - Classify each service (real debt vs false positive)
   - Recommend actions

### Phase 3: Signal Improvement (2 days)
1. **Scoring Algorithm Tuning**
   - Adjust anchor detection thresholds
   - Add composite-layer context
   - Improve service lifecycle awareness

2. **Create Improved Metrics**
   ```python
   # Example improved scoring
   def calculate_improved_retirement_score(service: ServiceInfo) -> float:
       base_score = calculate_base_score(service)
       composite_context = get_composite_context(service)
       return base_score * composite_context.weight
   ```

3. **Document Improvements**
   - Update technical debt policy
   - Add false positive handling guide
   - Improve signal documentation

## Success Criteria

- [ ] False positive rate reduced to ≤10%
- [ ] All flagged services classified
- [ ] Improved scoring algorithm implemented
- [ ] Documentation updated
- [ ] No real technical debt missed

## Verification Commands

```bash
# Re-run scoring with improved algorithm
python scripts/analyze_technical_debt.py --improved-scoring

# Compare before/after results
diff reports/technical-debt/before.md reports/technical-debt/after.md

# Validate no real debt was misclassified
grep -rn "deletion_score=8" reports/technical-debt/after.md | grep -v "FALSE_POSITIVE"
```

## Impact Assessment

**Positive Impacts:**
- More accurate technical debt detection
- Reduced false alarm fatigue
- Better resource allocation
- Improved trust in metrics

**Potential Risks:**
- Missing real technical debt
- Over-correction leading to missed signals
- Complexity in scoring algorithm

**Mitigation:**
- Manual validation of results
- Conservative tuning approach
- Clear documentation of changes

## Related Issues

- Depends: TD-08 (scoring calibration) - foundational work
- Related: TD-03, TD-04, TD-05 (specific service audits)

## Checklist

- [ ] Signal validation complete
- [ ] False positives identified
- [ ] Audit report created
- [ ] Scoring improvements implemented
- [ ] Documentation updated

## Time Estimate

**Total**: 7 days  
**Start**: 2024-05-05  
**Target Completion**: 2024-05-15

## Assignee

(TBD - comment on tracking issue to claim)

## Audit Classification System

| Classification | Criteria | Action |
|---------------|----------|--------|
| REAL_DEBT | No usage, no tests, no dependencies | Schedule for removal |
| FALSE_POSITIVE | Active usage, missing anchors | Improve signal detection |
| UNCLEAR | Mixed signals, needs investigation | Manual review required |
| LEGACY | Deprecated but needed | Document, schedule removal |

## Notes

This audit is critical for improving the accuracy of our technical debt detection. The results will feed directly into TD-08 (scoring calibration) to create a more reliable system.
