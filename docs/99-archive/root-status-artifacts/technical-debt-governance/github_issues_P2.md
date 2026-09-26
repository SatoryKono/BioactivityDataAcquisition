# GitHub Issues for P2 Technical Debt

## Issue 7: [P2-001] Add Observability Tracing Coverage

```markdown
## Description
Tracing coverage has gaps in several modules, making production debugging difficult and SLO enforcement ineffective.

## Impact
- **Blocks:** Production debugging, SLO monitoring
- **Current exemption:** `src/bioetl/infrastructure/observability/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Gap Analysis (1 day)
1. Identify modules with missing tracing
2. Document key paths without spans
3. Identify high cardinality label issues
4. Review metric declarations

### Phase 2: Implementation (2-3 days)
1. Add span instrumentation to key paths
2. Normalize label naming to avoid high cardinality
3. Align metric declarations with actual usage
4. Add span context propagation

### Phase 3: Validation (1 day)
1. Run tracing validation checks
2. Review span coverage
3. Verify label cardinality
4. Test metric alignment

### Phase 4: Cleanup (1 day)
1. Update observability configs
2. Remove observability exemption
3. Update architecture metrics baseline
4. Update documentation

## Owner
@bioetl-observability

## Effort
M (3-5 days)

## Dependencies
None

## Deadline
2027-01-31

## Related Files
- `src/bioetl/infrastructure/observability/`
- `config/observability_metric_declarations.yaml`
- `config/observability_metric_governance.yaml`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Key paths have span instrumentation
- [ ] Label cardinality normalized
- [ ] Metric declarations aligned with usage
- [ ] Observability configs updated
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P2-001
- `enforcement_strategy.md` - Enforcement strategy
- `observability_debt_audit.md` - Observability audit report
```

---

## Issue 8: [P2-002] Simplify DQ Analyzer Validation Rules

```markdown
## Description
Data quality analyzer has complex validation rule bundles that are hard to maintain.

## Impact
- **Blocks:** DQ rule maintenance
- **Current exemption:** `src/bioetl/application/services/dq/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Analyze validation rule patterns
2. Identify common rule templates
3. Document rule composition issues
4. Identify testability gaps

### Phase 2: Design (1 day)
1. Extract common rule templates
2. Design simplified rule composition
3. Plan refactoring strategy

### Phase 3: Implementation (1-2 days)
1. Create rule template library
2. Refactor validation rules to use templates
3. Simplify rule composition
4. Improve rule testability

### Phase 4: Testing (1 day)
1. Add tests for rule templates
2. Update existing rule tests
3. Add regression tests

### Phase 5: Cleanup (1 day)
1. Update DQ documentation
2. Remove DQ exemption
3. Update architecture metrics baseline
4. Update governance configs

## Owner
@bioetl-dq

## Effort
S (1-2 days)

## Dependencies
None

## Deadline
2027-01-31

## Related Files
- `src/bioetl/application/services/dq/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Rule templates implemented
- [ ] Validation rules simplified
- [ ] Rule testability improved
- [ ] All tests pass
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P2-002
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 9: [P2-003] Simplify Silver Storage Write Path

```markdown
## Description
Silver storage write path has complex coercion logic affecting performance.

## Impact
- **Blocks:** Storage performance improvements
- **Current exemption:** `src/bioetl/infrastructure/storage/silver/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Analyze write path coercion logic
2. Identify performance bottlenecks
3. Document coercion patterns
4. Benchmark current performance

### Phase 2: Design (1 day)
1. Extract common coercion helpers
2. Simplify branching in write path
3. Design performance optimization strategy

### Phase 3: Implementation (1-2 days)
1. Create coercion helper functions
2. Refactor write path to use helpers
3. Simplify branching logic
4. Optimize performance-critical paths

### Phase 4: Testing (1 day)
1. Add performance benchmarks
2. Update existing tests
3. Verify data integrity

### Phase 5: Cleanup (1 day)
1. Remove storage exemption
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-storage

## Effort
S (1-2 days)

## Dependencies
None

## Deadline
2027-01-31

## Related Files
- `src/bioetl/infrastructure/storage/silver/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Coercion helpers implemented
- [ ] Write path simplified
- [ ] Performance benchmarks added
- [ ] All tests pass
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P2-003
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 10: [P2-004] Simplify Control Plane Artifact Orchestration

```markdown
## Description
Control plane has complex artifact orchestration logic.

## Impact
- **Blocks:** Artifact management improvements
- **Current exemption:** `src/bioetl/infrastructure/control_plane/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Analyze artifact orchestration patterns
2. Identify orchestration complexity points
3. Document artifact lifecycle
4. Identify error handling gaps

### Phase 2: Design (1 day)
1. Extract common orchestration helpers
2. Simplify artifact lifecycle management
3. Design improved error handling

### Phase 3: Implementation (1-2 days)
1. Create orchestration helper functions
2. Refactor artifact lifecycle management
3. Improve error handling
4. Add logging and observability

### Phase 4: Testing (1 day)
1. Add integration tests
2. Update existing tests
3. Verify error handling

### Phase 5: Cleanup (1 day)
1. Remove control plane exemption
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-control-plane

## Effort
S (1-2 days)

## Dependencies
None

## Deadline
2027-01-31

## Related Files
- `src/bioetl/infrastructure/control_plane/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Orchestration helpers implemented
- [ ] Artifact lifecycle simplified
- [ ] Error handling improved
- [ ] All tests pass
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P2-004
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 11: [P2-005] Simplify Quarantine Normalization

```markdown
## Description
Quarantine has complex normalization branches.

## Impact
- **Blocks:** Quarantine processing improvements
- **Current exemption:** `src/bioetl/infrastructure/quarantine/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Analyze normalization branching patterns
2. Identify common normalization operations
3. Document quarantine processing flow
4. Identify edge cases

### Phase 2: Design (1 day)
1. Extract common normalization helpers
2. Simplify quarantine processing
3. Design integration test strategy

### Phase 3: Implementation (1-2 days)
1. Create normalization helper functions
2. Refactor quarantine processing
3. Simplify branching logic
4. Add error handling

### Phase 4: Testing (1 day)
1. Add integration tests
2. Update existing tests
3. Verify edge cases

### Phase 5: Cleanup (1 day)
1. Remove quarantine exemption
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-quarantine

## Effort
S (1-2 days)

## Dependencies
None

## Deadline
2027-01-31

## Related Files
- `src/bioetl/infrastructure/quarantine/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Normalization helpers implemented
- [ ] Quarantine processing simplified
- [ ] Integration tests added
- [ ] All tests pass
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P2-005
- `enforcement_strategy.md` - Enforcement strategy
```
