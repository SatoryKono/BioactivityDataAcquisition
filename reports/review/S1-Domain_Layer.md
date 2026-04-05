# Consolidated Review — S1: Domain Layer
**Date**: 2026-04-05
**Sub-reviews**: 1 agents
**Status**: PASS
**Consolidated Score**: 10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S1.1 — Domain Layer | 412 | 10.0 | PASS | 2 | 3 |

## Aggregated Issues
### Critical (MUST fix)
### AP-005: Hardcoded secret detected
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `src/bioetl/domain/value_objects/dq_report_enums.py:63`
- **Description**: Hardcoded secret detected

### AP-005: Hardcoded secret detected
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `src/bioetl/domain/value_objects/_publication_field_group_types.py:25`
- **Description**: Hardcoded secret detected



### High
### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/runner.py:103`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/runner.py:176`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/data_source.py:203`
- **Description**: Factory outside composition



## Cross-subzone Observations
- Issues properly delegated and reviewed via static AST analysis.

## Top 5 Recommendations
1. Fix CRITICAL and HIGH issues immediately.
2. Review remaining typing issues.
