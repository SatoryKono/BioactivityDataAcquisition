# GitHub Issues for P3 Technical Debt

## Issue 12: [P3-001] Centralize Provider Transformers in Registry

```markdown
## Description
Provider transformers are scattered across provider modules instead of being registered in a central registry, making it hard to discover and maintain transformer logic.

## Impact
- **Blocks:** Transformer discovery and maintenance
- **Current exemption:** Individual provider modules (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Inventory all provider transformers across modules
2. Identify transformer registration patterns
3. Document transformer dependencies
4. Identify registration gaps

### Phase 2: Design (1 day)
1. Design central transformer registry
2. Define transformer registration API
3. Plan migration strategy
4. Design backward compatibility layer

### Phase 3: Implementation (2-3 days)
1. Create transformer registry module
2. Implement registration API
3. Migrate existing transformers to registry
4. Add registry tests
5. Implement backward compatibility

### Phase 4: Testing (1 day)
1. Add integration tests for registry
2. Verify transformer discovery
3. Test backward compatibility
4. Add documentation

### Phase 5: Cleanup (1 day)
1. Update provider documentation
2. Remove individual exemptions
3. Update architecture metrics baseline
4. Update governance configs

## Owner
@bioetl-providers

## Effort
M (3-5 days)

## Dependencies
None

## Deadline
2027-02-28

## Related Files
- `src/bioetl/application/transformers/`
- `src/bioetl/infrastructure/providers/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Transformer registry implemented
- [ ] All transformers registered centrally
- [ ] Transformer discovery works
- [ ] Backward compatibility maintained
- [ ] All tests pass
- [ ] Exemptions removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P3-001
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 13: [P3-002] Standardize Provider Config Schemas

```markdown
## Description
Provider configs use inconsistent schemas, making provider integration error-prone and hard to validate.

## Impact
- **Blocks:** Provider integration reliability
- **Current exemption:** Individual provider config files (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Inventory all provider config schemas
2. Identify schema inconsistencies
3. Document config validation gaps
4. Identify common config patterns

### Phase 2: Design (1 day)
1. Define standard config schema
2. Design config validation framework
3. Plan migration strategy
4. Design backward compatibility layer

### Phase 3: Implementation (2-3 days)
1. Create standard config schema definitions
2. Implement config validation
3. Migrate existing configs to standard schema
4. Add config validation tests
5. Implement backward compatibility

### Phase 4: Testing (1 day)
1. Add schema validation tests
2. Verify config migration
3. Test backward compatibility
4. Add documentation

### Phase 5: Cleanup (1 day)
1. Update provider documentation
2. Remove individual exemptions
3. Update architecture metrics baseline
4. Update governance configs

## Owner
@bioetl-providers

## Effort
M (3-5 days)

## Dependencies
None

## Deadline
2027-02-28

## Related Files
- `config/providers/`
- `src/bioetl/infrastructure/providers/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Standard config schema defined
- [ ] Config validation implemented
- [ ] All configs migrated to standard schema
- [ ] Backward compatibility maintained
- [ ] All tests pass
- [ ] Exemptions removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P3-002
- `enforcement_strategy.md` - Enforcement strategy
```

---

## Issue 14: [P3-003] Refactor Provider Adapters to Use Generic Base

```markdown
## Description
Provider adapters have duplicate logic and don't use a common base class, leading to code duplication and inconsistent behavior.

## Impact
- **Blocks:** Provider adapter consistency
- **Current exemption:** Individual provider adapters (xenon + critical_check)

## Resolution Plan

### Phase 1: Analysis (1 day)
1. Inventory all provider adapters
2. Identify duplicate adapter logic
3. Document adapter patterns
4. Identify adapter differences

### Phase 2: Design (1 day)
1. Design generic adapter base class
2. Define adapter interface
3. Plan refactoring strategy
4. Design backward compatibility layer

### Phase 3: Implementation (2-3 days)
1. Create generic adapter base class
2. Implement common adapter logic
3. Refactor existing adapters to use base
4. Add adapter tests
5. Implement backward compatibility

### Phase 4: Testing (1 day)
1. Add adapter integration tests
2. Verify adapter behavior
3. Test backward compatibility
4. Add documentation

### Phase 5: Cleanup (1 day)
1. Update provider documentation
2. Remove individual exemptions
3. Update architecture metrics baseline
4. Update governance configs

## Owner
@bioetl-providers

## Effort
M (3-5 days)

## Dependencies
None

## Deadline
2027-02-28

## Related Files
- `src/bioetl/infrastructure/providers/`
- `config/governance/duplication_complexity_exemptions.yaml`

## Acceptance Criteria
- [ ] Generic adapter base implemented
- [ ] All adapters use base class
- [ ] Duplicate logic eliminated
- [ ] Backward compatibility maintained
- [ ] All tests pass
- [ ] Exemptions removed
- [ ] Documentation updated

## References
- `technical_debt_backlog.md` - P3-003
- `enforcement_strategy.md` - Enforcement strategy
```