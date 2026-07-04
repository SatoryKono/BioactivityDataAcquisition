# Issue: Scripts Governance Audit and Cleanup

## Type
- [ ] Feature
- [ ] Bug
- [x] Technical Debt
- [ ] Documentation

## Priority
- [ ] P0 (Critical)
- [x] P1 (High)
- [ ] P2 (Medium)
- [ ] Low

## Context
Based on the architecture audit (2025-01-30), the scripts governance requires attention. There are 88 entries in `configs/quality/scripts_lifecycle_registry.json` that need classification and planning for cleanup.

## Problem
- 88 entries in lifecycle registry require review
- Categories breakdown:
  - 22 windows_compatibility_wrapper (PowerShell wrappers for Linux scripts)
  - 32 legacy_manual_utility (historical utilities with no active callers)
  - 22 shared_helper_module (shared helpers consumed by multiple scripts)
  - 5 compatibility_wrapper (compatibility shims for legacy tools)
  - 6 internal_helper_orphan (internal helpers with limited scope)
  - 1 internal_compatibility_launcher
- Technical debt accumulation in scripts layer
- Unclear ownership and lifecycle for many scripts

## Impact
- Maintenance burden
- Unclear ownership
- Technical debt accumulation
- Potential security risks (legacy utilities with .env dependencies)
- CI complexity

## Proposed Solution

### Phase 1: Audit and Classification (Week 1)
1. Review all 88 entries in lifecycle registry
2. Identify scripts with no active callers
3. Identify scripts with security risks (.env dependencies)
4. Classify each entry by:
   - Active usage (has callers)
   - Security risk (secrets, .env)
   - Maintenance burden
   - Migration path

### Phase 2: Windows Wrappers Consolidation (Week 2)
Target: 22 windows_compatibility_wrapper entries
- Audit which wrappers are actively used
- Consolidate duplicate wrappers
- Document Windows/WSL compatibility strategy
- Remove obsolete wrappers

### Phase 3: Legacy Utilities Retirement (Week 3-4)
Target: 32 legacy_manual_utility entries
- Identify utilities with no active callers
- Deprecate with warnings (2 weeks)
- Remove deprecated utilities
- Update documentation

### Phase 4: Compatibility Shims Removal (Week 5)
Target: 5 compatibility_wrapper entries
- Audit callers for each shim
- Migrate callers to canonical paths
- Remove shims
- Update governance tests

### Phase 5: Shared Helpers Consolidation (Week 6)
Target: 22 shared_helper_module entries
- Consolidate duplicate helpers
- Promote to active inventory where appropriate
- Document shared helper API
- Update imports

## Implementation Steps

### Step 1: Audit
```bash
# Analyze all 88 entries
python scripts/engineering/qa/audit_scripts_lifecycle.py
```

### Step 2: Create removal plan
Document for each entry:
- Current usage
- Migration path
- Removal timeline
- Owner approval

### Step 3: Execute cleanup
- Remove obsolete scripts
- Update lifecycle registry
- Update architecture tests
- Update documentation

## Acceptance Criteria
- [ ] All 88 entries audited and classified
- [ ] Removal plan documented
- [ ] Windows wrappers reduced to ≤10
- [ ] Legacy utilities reduced to ≤10
- [ ] Compatibility shims reduced to 0
- [ ] Shared helpers consolidated
- [ ] Lifecycle registry updated
- [ ] Architecture tests pass
- [ ] CI passes

## Evidence
- Architecture audit score: Technical Debt 8.0/10
- Lifecycle registry: `configs/quality/scripts_lifecycle_registry.json`
- Total scripts: 295
- Registry entries: 88

## Related Issues
- Architecture audit 2025-01-30
- Technical debt reduction
- Scripts governance

## Labels
`technical-debt`, `scripts`, `governance`, `cleanup`

## Estimate
40 hours (6 weeks)
