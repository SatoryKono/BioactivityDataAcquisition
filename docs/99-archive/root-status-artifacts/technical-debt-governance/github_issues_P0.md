# GitHub Issues for P0 Technical Debt

## Issue 1: [P0-001] Extract Adapter Fallback Logic into Policy Helpers

```markdown
## Description
Currently, 7 adapters (ChEMBL, OpenAlex, Semantic Scholar, CrossRef, PubMed, UniProt, PubChem) embed fallback logic directly in adapter code, causing high cyclomatic complexity. This blocks layering cleanup, test simplification, and observability improvements.

## Impact
- **Blocks:** Layering cleanup, test simplification, observability
- **Affects:** All external provider integrations
- **Current exemptions:** 7 adapters with xenon + critical_check (expires 2026-12-31)

## Resolution Plan

### Phase 1: Design (1-2 days)
1. Design a unified fallback policy interface
2. Define policy configuration schema
3. Document policy helper patterns

### Phase 2: Implementation (5-7 days)
1. Extract `fetch_filtered_with_fallback` pattern into reusable helper
2. Extract `_request_with_retry` pattern into reusable helper
3. Create policy helper module in `src/bioetl/infrastructure/adapters/common/`

### Phase 3: Migration (3-5 days)
1. Migrate ChEMBL adapter to use new helpers
2. Migrate OpenAlex adapter to use new helpers
3. Migrate Semantic Scholar adapter to use new helpers
4. Migrate CrossRef adapter to use new helpers
5. Migrate PubMed adapter to use new helpers
6. Migrate UniProt adapter to use new helpers
7. Migrate PubChem adapter to use new helpers

### Phase 4: Testing (1-2 days)
1. Update tests to mock policy helpers instead of adapters
2. Add integration tests for policy helpers
3. Verify all adapter tests pass

### Phase 5: Cleanup (1 day)
1. Remove 7 adapter exemptions from `config/governance/duplication_complexity_exemptions.yaml`
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-platform

## Effort
L (1-2 weeks)

## Dependencies
None

## Deadline
2026-12-31 (exemption expiration)

## Related Files
- `src/bioetl/infrastructure/adapters/chembl/`
- `src/bioetl/infrastructure/adapters/openalex/`
- `src/bioetl/infrastructure/adapters/semantic_scholar/`
- `src/bioetl/infrastructure/adapters/crossref/`
- `src/bioetl/infrastructure/adapters/pubmed/`
- `src/bioetl/infrastructure/adapters/uniprot/`
- `src/bioetl/infrastructure/adapters/pubchem/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] All 7 adapters use unified policy helpers
- [ ] Cyclomatic complexity reduced below thresholds
- [ ] All adapter tests pass
- [ ] All exemptions removed from config
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P0-001
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 2: [P0-002] Simplify Composite Orchestration Branching

```markdown
## Description
Composite orchestration (join, checkpoint, runner) has wide branching surfaces that block testability and debuggability. The wide dependency surfaces make refactoring unsafe and feature addition risky.

## Impact
- **Blocks:** Unit test coverage, debugging, refactoring, feature addition
- **Current exemption:** `src/bioetl/application/composite/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1-2 days)
1. Analyze branching patterns in merge/checkpoint collaborators
2. Map dependency surfaces between components
3. Identify refactoring safe zones

### Phase 2: Component Split (3-5 days)
1. Split merge collaborator into focused sub-components
2. Split checkpoint collaborator into focused sub-components
3. Extract shared logic into helper modules
4. Define clear interfaces between components

### Phase 3: Dependency Reduction (2-3 days)
1. Reduce dependency surfaces between collaborators
2. Introduce dependency injection where needed
3. Simplify constructor signatures

### Phase 4: Testing (2-3 days)
1. Add integration tests for split components
2. Add unit tests for extracted helpers
3. Verify all composite orchestration tests pass

### Phase 5: Observability (1 day)
1. Update observability to trace split components
2. Add metrics for component performance
3. Update dashboards

### Phase 6: Cleanup (1 day)
1. Remove composite orchestration exemption
2. Update architecture metrics baseline
3. Update documentation

## Owner
@bioetl-composite

## Effort
L (1-2 weeks)

## Dependencies
None

## Deadline
2026-12-31

## Related Files
- `src/bioetl/application/composite/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Composite orchestration split into focused components
- [ ] Dependency surfaces reduced
- [ ] Unit test coverage > 80%
- [ ] All tests pass
- [ ] Exemption removed from config
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P0-002
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 3: [P0-003] Unify Runtime Builder and CLI Wiring

```markdown
## Description
Runtime builders and CLI have duplicated command wiring and policy extraction logic. This blocks CLI/Runtime unification and configuration simplification.

## Impact
- **Blocks:** CLI/Runtime unification, configuration simplification
- **Current exemptions:**
  - `src/bioetl/composition/runtime_builders/` (xenon + critical_check)
  - `src/bioetl/composition/factories/services/` (xenon + critical_check)
  - `src/bioetl/interfaces/cli/` (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1-2 days)
1. Map duplicated command wiring logic
2. Map duplicated policy extraction logic
3. Identify differences between CLI and runtime implementations
4. Design unified wiring abstraction

### Phase 2: Implementation (3-5 days)
1. Extract multi-source extraction logic into shared helpers
2. Create unified command wiring abstraction
3. Create shared policy extraction module
4. Define common interfaces

### Phase 3: Migration (3-5 days)
1. Migrate runtime builders to use unified wiring
2. Migrate service factories to use unified wiring
3. Migrate CLI to use unified wiring
4. Ensure feature parity between CLI and runtime

### Phase 4: Testing (2-3 days)
1. Update tests for unified wiring
2. Add contract tests for unified interfaces
3. Verify CLI and runtime behavior parity
4. Add integration tests

### Phase 5: Cleanup (1 day)
1. Remove runtime builder exemption
2. Remove service factory exemption
3. Remove CLI exemption
4. Update architecture metrics baseline
5. Update documentation

## Owner
@bioetl-composition

## Effort
L (1-2 weeks)

## Dependencies
None

## Deadline
2026-12-31

## Related Files
- `src/bioetl/composition/runtime_builders/`
- `src/bioetl/composition/factories/services/`
- `src/bioetl/interfaces/cli/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Unified wiring abstraction implemented
- [ ] Runtime builders migrated
- [ ] Service factories migrated
- [ ] CLI migrated
- [ ] Feature parity achieved
- [ ] All tests pass
- [ ] All exemptions removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P0-003
- `enforcement_strategy.md` - Enforcement strategy
```
