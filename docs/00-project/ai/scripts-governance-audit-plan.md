# Scripts Governance Audit and Cleanup Plan

## Overview

This document provides the audit and cleanup plan for the 88 entries in `configs/quality/scripts_lifecycle_registry.json`.

## Current State

Based on the architecture audit (2025-01-30):
- Total scripts: 295
- Registry entries: 88
- Lifecycle registry: `configs/quality/scripts_lifecycle_registry.json`

## Classification Breakdown

| Category | Count | Description |
|----------|-------|-------------|
| windows_compatibility_wrapper | 22 | PowerShell wrappers for Linux scripts |
| legacy_manual_utility | 32 | Historical utilities with no active callers |
| shared_helper_module | 22 | Shared helpers consumed by multiple scripts |
| compatibility_wrapper | 5 | Compatibility shims for legacy tools |
| internal_helper_orphan | 6 | Internal helpers with limited scope |
| internal_compatibility_launcher | 1 | Internal compatibility launcher |

## Phase 1: Audit and Classification (Week 1)

### Objectives
- Review all 88 entries in lifecycle registry
- Identify scripts with no active callers
- Identify scripts with security risks (.env dependencies)
- Classify each entry by:
  - Active usage (has callers)
  - Security risk (secrets, .env)
  - Maintenance burden
  - Migration path

### Audit Script
```bash
# Analyze all 88 entries
python scripts/engineering/qa/audit_scripts_lifecycle.py
```

### Classification Matrix

| Script | Active Callers | Security Risk | Maintenance Burden | Migration Path | Action |
|--------|---------------|---------------|-------------------|----------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD |

## Phase 2: Windows Wrappers Consolidation (Week 2)

### Target
Reduce 22 `windows_compatibility_wrapper` entries to ≤10.

### Strategy
1. Audit which wrappers are actively used
2. Consolidate duplicate wrappers
3. Document Windows/WSL compatibility strategy
4. Remove obsolete wrappers

### Consolidation Plan

| Wrapper | Active Usage | Duplicate Of | Action | Timeline |
|---------|--------------|--------------|--------|----------|
| TBD | TBD | TBD | TBD | TBD |

## Phase 3: Legacy Utilities Retirement (Week 3-4)

### Target
Reduce 32 `legacy_manual_utility` entries to ≤10.

### Strategy
1. Identify utilities with no active callers
2. Deprecate with warnings (2 weeks)
3. Remove deprecated utilities
4. Update documentation

### Retirement Plan

| Utility | Active Callers | Deprecation Date | Removal Date | Action |
|---------|---------------|------------------|--------------|--------|
| TBD | TBD | TBD | TBD | TBD |

## Phase 4: Compatibility Shims Removal (Week 5)

### Target
Reduce 5 `compatibility_wrapper` entries to 0.

### Strategy
1. Audit callers for each shim
2. Migrate callers to canonical paths
3. Remove shims
4. Update governance tests

### Shim Migration Plan

| Shim | Callers | Canonical Path | Migration Status | Removal Date |
|------|---------|----------------|------------------|--------------|
| TBD | TBD | TBD | TBD | TBD |

## Phase 5: Shared Helpers Consolidation (Week 6)

### Target
Consolidate 22 `shared_helper_module` entries.

### Strategy
1. Consolidate duplicate helpers
2. Promote to active inventory where appropriate
3. Document shared helper API
4. Update imports

### Consolidation Plan

| Helper | Duplicates | Consolidated Location | API Documentation | Action |
|--------|------------|----------------------|-------------------|--------|
| TBD | TBD | TBD | TBD | TBD |

## Implementation Steps

### Step 1: Audit
```bash
# Analyze all 88 entries
python scripts/engineering/qa/audit_scripts_lifecycle.py

# Generate classification matrix
python scripts/engineering/qa/generate_scripts_classification_matrix.py
```

### Step 2: Create Removal Plan
Document for each entry:
- Current usage
- Migration path
- Removal timeline
- Owner approval

### Step 3: Execute Cleanup
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

## Estimate

40 hours (6 weeks)

## Notes

This plan is a starting point. The actual audit may reveal different numbers and classifications. The plan should be updated as audit results become available.
