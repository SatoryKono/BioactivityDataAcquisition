---
title: "[P5] Metrics cardinality audit and high-cardinality label review"
labels: priority/P5, technical-debt, observability, enhancement
assignees: []
---

## Context

Technical debt audit identified potential **observability gap** in metrics governance. There is no automated check for high-cardinality labels in Prometheus metrics, which can lead to performance issues and increased costs.

## Current State

- **Metric inventory script**: `report_observability_metric_inventory.py` exists
- **Automated checking**: Not integrated into CI
- **High-cardinality detection**: Manual process only
- **Governance gap**: No enforcement for label cardinality

## Problem

1. **Performance risk**: High-cardinality metrics can impact Prometheus performance
2. **Cost impact**: Unbounded cardinality increases storage costs
3. **No enforcement**: New high-cardinality metrics can be introduced without review
4. **Manual process**: Current audit requires manual execution and review

## Impact

- **Risk**: Low - no specific high-cardinality issues identified, but governance gap exists
- **Effort**: Medium - integrate existing script into CI, establish thresholds

## Proposed Solution

### Phase 1: Audit Execution (Week 1)
1. Run `report_observability_metric_inventory.py`
2. Analyze output for high-cardinality labels
3. Identify metrics exceeding reasonable cardinality thresholds
4. Document findings and recommendations

### Phase 2: Threshold Definition (Week 1-2)
1. Define cardinality thresholds per metric type (counters, gauges, histograms)
2. Document acceptable label cardinality patterns
3. Establish review process for exceptions
4. Add governance policy to project rules

### Phase 3: CI Integration (Week 2-3)
1. Integrate `report_observability_metric_inventory.py` into CI pipeline
2. Add automated check for cardinality threshold violations
3. Configure fail-fast for new violations
4. Add exception process for legitimate high-cardinality use cases

### Phase 4: Remediation (Week 3-4)
1. Address identified high-cardinality issues
2. Refactor metrics to reduce cardinality where appropriate
3. Document legitimate high-cardinality use cases with justification
4. Update metric documentation

## Acceptance Criteria

- [ ] Metrics cardinality audit completed
- [ ] Cardinality thresholds defined and documented
- [ ] Automated check integrated into CI
- [ ] Governance policy added to project rules
- [ ] Identified high-cardinality issues addressed or documented
- [ ] Metric documentation updated
- [ ] All tests pass

## Related Files

- `report_observability_metric_inventory.py` (script location to be verified)
- Metric definition files across codebase
- `docs/00-project/RULES.md` (for governance policy)
- CI configuration files

## References

- Technical Debt Audit: Observability gap analysis
- Prometheus best practices for label cardinality

## Notes

This is **P5 priority** because no specific high-cardinality issues were identified, but the governance gap represents a future risk. Focus on establishing automated prevention rather than reactive remediation.