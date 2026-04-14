# TD-08: Calibrate Composite-Layer Retirement and Complexity Scoring

**Status**: Open  
**Priority**: P2  
**Labels**: `technical-debt`, `metrics`, `tooling`, `improvement`  
**Epic**: Technical Debt Wave 2024Q2

## Problem

Current retirement/complexity scoring shows:
- Too many deletion_score=8 with 0/0/0/0 anchors
- False positives in clearly live modules
- Lack of trust in signal accuracy
- Poor composite-layer specificity

## Root Cause

Current scoring algorithm lacks:
- Composite-layer context awareness
- Proper anchor detection for services
- Nuanced understanding of service lifecycles
- Domain-specific knowledge

## Scope

**Affected Components:**
- Technical debt detection scripts
- Scoring algorithms
- Signal processing pipeline

**Impact Analysis:**
```bash
# Check current false positive rate
grep "deletion_score=8" reports/technical-debt/current.md | wc -l
grep "FALSE_POSITIVE" reports/technical-debt/audit.md | wc -l
```

## Solution Plan

### Phase 1: Analysis (2 days)
1. **Current Algorithm Review**
   - Examine existing scoring logic
   - Identify limitations
   - Document current behavior

2. **False Positive Analysis**
   - Review TD-06 audit results
   - Identify common patterns
   - Document signal limitations

3. **Composite-Layer Requirements**
   - Interview domain experts
   - Document composite-specific patterns
   - Identify missing context

### Phase 2: Design (1 day)
1. **Improved Scoring Algorithm**
   ```python
   # Example improved scoring
   def calculate_composite_retirement_score(
       service: ServiceInfo,
       composite_context: CompositeContext
   ) -> float:
       base_score = calculate_base_score(service)
       
       # Add composite-layer context
       composite_weight = calculate_composite_weight(service, composite_context)
       
       # Adjust for service lifecycle
       lifecycle_adjustment = get_lifecycle_adjustment(service)
       
       return base_score * composite_weight * lifecycle_adjustment
   ```

2. **Anchor Detection Improvement**
   - Add composite-layer specific anchors
   - Improve service dependency detection
   - Add dynamic analysis capabilities

### Phase 3: Implementation (1 day)
1. **Update Scoring Scripts**
   - Implement improved algorithm
   - Add composite context detection
   - Improve anchor detection

2. **Add Validation Checks**
   - False positive detection
   - Signal confidence scoring
   - Manual override capabilities

### Phase 4: Validation (1 day)
1. **Test Improved Scoring**
   ```bash
   # Run improved scoring
   python scripts/analyze_technical_debt.py --improved --output reports/technical-debt/improved.md
   
   # Compare results
   diff reports/technical-debt/before.md reports/technical-debt/improved.md
   ```

2. **Manual Validation**
   - Review high-score items
   - Validate signal accuracy
   - Adjust thresholds as needed

3. **Documentation Update**
   - Update technical debt policy
   - Add scoring methodology docs
   - Create user guide

## Success Criteria

- [ ] False positive rate reduced to ≤10%
- [ ] Signal confidence improved
- [ ] Composite-layer context added
- [ ] Documentation updated
- [ ] Validation process established

## Verification Commands

```bash
# Calculate false positive rate
python scripts/validate_scoring.py --input reports/technical-debt/improved.md

# Run full analysis
python scripts/analyze_technical_debt.py --full --output reports/technical-debt/final.md

# Generate comparison report
python scripts/compare_scoring.py --before reports/technical-debt/before.md --after reports/technical-debt/after.md
```

## Impact Assessment

**Positive Impacts:**
- More accurate technical debt detection
- Better resource allocation
- Improved trust in metrics
- Reduced false alarm fatigue

**Potential Risks:**
- Over-correction missing real debt
- Increased complexity in scoring
- Maintenance burden

**Mitigation:**
- Conservative tuning approach
- Manual validation process
- Clear documentation

## Related Issues

- Depends: TD-06 (zero-anchor audit) - provides data for calibration
- Foundational for all other issues - improves signal accuracy

## Checklist

- [ ] Current algorithm analyzed
- [ ] Improved algorithm designed
- [ ] Implementation complete
- [ ] Validation successful
- [ ] Documentation updated

## Time Estimate

**Total**: 5 days  
**Start**: 2024-05-20  
**Target Completion**: 2024-05-28

## Assignee

(TBD - comment on tracking issue to claim)

## Future Improvements

This calibration establishes a foundation for:
- Automated signal validation
- Machine learning-based scoring
- Continuous improvement pipeline
- Better integration with development workflow

## Notes

This issue is foundational for improving the accuracy of all technical debt detection. The results will feed back into TD-06 and help validate the findings from other issues in this wave.
