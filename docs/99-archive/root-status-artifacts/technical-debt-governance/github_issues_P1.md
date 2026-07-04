# GitHub Issues for P1 Technical Debt

## Issue 4: [P1-001] Fix Domain ↔ Infrastructure Layering Violations

```markdown
## Description
Domain entities import infrastructure components, and infrastructure depends on domain internals. This blocks domain testing in isolation, infrastructure replacement, and safe refactoring.

## Impact
- **Blocks:** Domain testing in isolation, infrastructure replacement, domain evolution
- **Dependencies:** Made worse by adapter complexity (P0-001)

## Resolution Plan

### Phase 1: Analysis (2-3 days)
1. Map all Domain → Infrastructure violations
2. Map all Infrastructure → Domain violations
3. Identify circular dependencies
4. Document violation patterns

### Phase 2: Design (2-3 days)
1. Design clean boundary interfaces
2. Define anti-corruption layer patterns
3. Plan refactoring safe zones
4. Create migration strategy

### Phase 3: Refactoring (7-10 days)
1. Refactor domain entities to remove infrastructure imports
2. Introduce anti-corruption layers where needed
3. Update infrastructure to respect domain boundaries
4. Ensure dependency direction is correct

### Phase 4: Testing (2-3 days)
1. Update tests to respect layering
2. Add architecture tests to prevent regression
3. Verify domain tests run in isolation
4. Verify infrastructure tests work with new boundaries

### Phase 5: Cleanup (1 day)
1. Update architecture metrics baseline
2. Update documentation
3. Update governance configs

## Owner
@bioetl-architecture

## Effort
XL (2-3 weeks)

## Dependencies
P0-001 (Adapter complexity cleanup)

## Deadline
2027-03-31

## Related Files
- `src/bioetl/domain/`
- `src/bioetl/infrastructure/`
- `config/governance/architecture_metric_exemptions.yaml`

## Acceptance Criteria
- [ ] All Domain → Infrastructure violations resolved
- [ ] All Infrastructure → Domain violations resolved
- [ ] Circular dependencies eliminated
- [ ] Domain tests run in isolation
- [ ] Architecture tests prevent regression
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P1-001
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 5: [P1-002] Standardize Extractor Parsing Logic

```markdown
## Description
Parsing logic is duplicated across multiple pipelines' extractors, causing bug propagation and maintenance overhead.

## Impact
- **Blocks:** Bug fixes, maintenance
- **Current exemption:** `src/bioetl/application/pipelines/*/extractors/*` (xenon)
- **Dependencies:** Similar patterns to adapter complexity (P0-001)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Identify common parsing patterns across extractors
2. Document parsing variations
3. Identify bugs caused by duplication

### Phase 2: Design (1 day)
1. Design unified parsing helper library
2. Define parsing interface
3. Plan migration strategy

### Phase 3: Implementation (2-3 days)
1. Create unified parsing helper module
2. Implement common parsing functions
3. Add tests for parsing helpers

### Phase 4: Migration (2-3 days)
1. Migrate ChEMBL extractor to use helpers
2. Migrate OpenAlex extractor to use helpers
3. Migrate other extractors to use helpers
4. Verify feature parity

### Phase 5: Testing (1 day)
1. Update tests for unified parsing
2. Add regression tests
3. Verify all extractor tests pass

### Phase 6: Cleanup (1 day)
1. Remove extractor exemption
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-application

## Effort
M (3-5 days)

## Dependencies
P0-001 (Learn from adapter refactoring)

## Deadline
2027-01-31

## Related Files
- `src/bioetl/application/pipelines/*/extractors/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Unified parsing helper library implemented
- [ ] All extractors migrated to use helpers
- [ ] Parsing bugs fixed
- [ ] All tests pass
- [ ] Exemption removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P1-002
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 6: [P1-003] Improve Testability of Complex Components

```markdown
## Description
Complex components (composite orchestration, adapters, runtime builders) are hard to test due to wide branching and dependency surfaces.

## Impact
- **Blocks:** Test coverage, confidence in refactoring
- **Dependencies:** P0-001, P0-002, P0-003

## Resolution Plan

### Phase 1: Unit Tests for Adapters (3-5 days)
1. Add unit tests for simplified adapters (after P0-001)
2. Mock policy helpers instead of full adapters
3. Test fallback logic in isolation
4. Add error scenario tests

### Phase 2: Integration Tests for Orchestration (3-5 days)
1. Add integration tests for split orchestration (after P0-002)
2. Test component interactions
3. Add end-to-end workflow tests
4. Add performance tests

### Phase 3: Contract Tests for Wiring (2-3 days)
1. Add contract tests for unified wiring (after P0-003)
2. Test CLI/Runtime parity
3. Test configuration loading
4. Test error handling

### Phase 4: Test Infrastructure (2-3 days)
1. Improve fixture reuse across tests
2. Reduce test flakiness
3. Improve test execution time
4. Add test coverage reporting

### Phase 5: Validation (1-2 days)
1. Verify test coverage targets met
2. Run full test suite
3. Identify remaining gaps
4. Update documentation

## Owner
@bioetl-data-platform

## Effort
L (1-2 weeks)

## Dependencies
P0-001, P0-002, P0-003

## Deadline
2027-02-28

## Related Files
- `tests/bioetl/infrastructure/adapters/`
- `tests/bioetl/application/composite/`
- `tests/bioetl/composition/`

## Acceptance Criteria
- [ ] Unit test coverage > 80% for adapters
- [ ] Integration tests for orchestration added
- [ ] Contract tests for wiring added
- [ ] Test flakiness reduced
- [ ] Test execution time improved
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P1-003
- `enforcement_strategy.md` - Enforcement strategy
```
