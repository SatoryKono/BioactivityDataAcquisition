# GitHub Issue Design for Reproducibility Issues

## Purpose

This document provides templates and guidelines for creating GitHub issues when reproducibility violations are found during audit.

## Issue Template

```markdown
## Reproducibility Violation Found

**Severity:** [High/Medium/Low]
**Component:** [component_name]
**Audit Date:** [timestamp]
**Auditor:** [agent/skill]

### Summary

[Brief description of the reproducibility violation]

### Violation Type

- [ ] Determinism violation
- [ ] Test coverage insufficient
- [ ] I/O non-determinism
- [ ] Schema validation missing
- [ ] Logging issue
- [ ] Dependency issue
- [ ] Breaking change undocumented

### Details

**File:** [file_path]
**Line:** [line_number]
**Pattern:** [violation_pattern]

**Code:**
```python
[code_snippet]
```

**Risk:**
[Description of risk]

### Impact

- [ ] Breaks replay capability
- [ ] Causes non-deterministic behavior
- [ ] Reduces test reliability
- [ ] Exposes secrets
- [ ] Breaking change without documentation

### Recommended Fix

[Description of recommended fix]

**Example:**
```python
[fixed_code_snippet]
```

### Acceptance Criteria

- [ ] Fix implements deterministic pattern
- [ ] Tests added for new code paths
- [ ] Schema validation in place
- [ ] Structured logging used
- [ ] Dependencies pinned
- [ ] Breaking changes documented

### Priority

**Priority:** [P0/P1/P2/P3]

**Rationale:**
[Justification for priority]

### Related

- [ ] ADR
- [ ] Requirement
- [ ] Related issue
- [ ] Related PR
```

## Example Issues

### Example 1: Non-Deterministic DataFrame Operation

```markdown
## Reproducibility Violation Found

**Severity:** High
**Component:** src/bioetl/pipelines/chembl/activity.py
**Audit Date:** 2026-01-21T10:00:00Z
**Auditor:** py-reproducibility-audit

### Summary

Non-deterministic DataFrame operation found - `df.head(10)` without stable sorting.

### Violation Type

- [x] Determinism violation
- [ ] Test coverage insufficient
- [ ] I/O non-determinism
- [ ] Schema validation missing
- [ ] Logging issue
- [ ] Dependency issue
- [ ] Breaking change undocumented

### Details

**File:** src/bioetl/pipelines/chembl/activity.py
**Line:** 145
**Pattern:** Unsorted DataFrame head operation

**Code:**
```python
result = df.head(10)
```

**Risk:**
Results will vary between runs, breaking replay capability and causing inconsistent test results.

### Impact

- [x] Breaks replay capability
- [x] Causes non-deterministic behavior
- [x] Reduces test reliability
- [ ] Exposes secrets
- [ ] Breaking change without documentation

### Recommended Fix

Add stable sorting before head operation:

```python
result = df.sort_values("activity_id").head(10)
```

### Acceptance Criteria

- [x] Fix implements deterministic pattern
- [ ] Tests added for new code paths
- [ ] Schema validation in place
- [ ] Structured logging used
- [ ] Dependencies pinned
- [ ] Breaking changes documented

### Priority

**Priority:** P0

**Rationale:**
High severity - breaks core reproducibility invariant, affects all downstream consumers.

### Related

- [ ] ADR-001: Determinism Requirements
- [ ] REQ-045: Reproducibility
```

### Example 2: Insufficient Test Coverage

```markdown
## Reproducibility Violation Found

**Severity:** Medium
**Component:** src/bioetl/clients/chembl.py
**Audit Date:** 2026-01-21T11:00:00Z
**Auditor:** py-reproducibility-audit

### Summary

Test coverage for new function `fetch_activity_data` is 65%, below 80% threshold.

### Violation Type

- [ ] Determinism violation
- [x] Test coverage insufficient
- [ ] I/O non-determinism
- [ ] Schema validation missing
- [ ] Logging issue
- [ ] Dependency issue
- [ ] Breaking change undocumented

### Details

**File:** src/bioetl/clients/chembl.py
**Line:** 78-120
**Pattern:** New function without adequate test coverage

**Code:**
```python
def fetch_activity_data(self, activity_ids: List[str]) -> pd.DataFrame:
    # Implementation
    pass
```

**Risk:**
Untested code paths may contain bugs that only manifest in production, reducing reliability.

### Impact

- [ ] Breaks replay capability
- [ ] Causes non-deterministic behavior
- [x] Reduces test reliability
- [ ] Exposes secrets
- [ ] Breaking change without documentation

### Recommended Fix

Add unit tests for all code paths:

```python
def test_fetch_activity_data_success():
    # Test successful fetch
    pass


def test_fetch_activity_data_empty():
    # Test empty result
    pass


def test_fetch_activity_data_error():
    # Test error handling
    pass
```

### Acceptance Criteria

- [ ] Fix implements deterministic pattern
- [x] Tests added for new code paths
- [ ] Schema validation in place
- [ ] Structured logging used
- [ ] Dependencies pinned
- [ ] Breaking changes documented

### Priority

**Priority:** P1

**Rationale:**
Medium severity - affects test reliability but doesn't break core invariants.

### Related

- [ ] REQ-089: Test Coverage Requirements
```

## Severity Guidelines

| Severity | Criteria | Response Time |
| -------- | -------- | ------------- |
| High | Breaks core invariant, affects replay capability | Immediate |
| Medium | Reduces reliability, below threshold | Within 1 day |
| Low | Cosmetic, documentation only | Within 1 week |

## Priority Guidelines

| Priority | Severity | Impact | Example |
| -------- | -------- | ------ | ------- |
| P0 | High | Critical path | Non-deterministic core operation |
| P1 | Medium | Important feature | Insufficient test coverage |
| P2 | Low | Nice to have | Documentation gap |
| P3 | Low | Backlog | Minor cosmetic issue |

## Labels

Use these labels for reproducibility issues:

- `reproducibility`
- `determinism`
- `test-coverage`
- `schema-validation`
- `logging`
- `dependencies`
- `breaking-change`

## Checklist

Before creating issue:

- [ ] Violation confirmed in audit
- [ ] File and line identified
- [ ] Risk assessed
- [ ] Impact documented
- [ ] Recommended fix proposed
- [ ] Acceptance criteria defined
- [ ] Priority justified
- [ ] Related artifacts linked
