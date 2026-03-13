# Consolidated Review — S1: Domain
**Date**: 2026-03-13
**Sub-reviews**: 5 agents
**Status**: PASS
**Consolidated Score**: 9.8/10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S1.1 — ports | 76 | 9.9 | PASS | 0 | 0 |
| S1.2 — entities | 65 | 9.9 | PASS | 0 | 0 |
| S1.3 — schemas | 41 | 10.0 | PASS | 0 | 0 |
| S1.4 — services | 49 | 9.9 | PASS | 0 | 0 |
| S1.5 — other | 84 | 9.4 | PASS | 0 | 3 |

## Aggregated Issues
### High

### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:56`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:95`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:129`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
  ```
## Cross-subzone Observations
- Verified zero overlap between subzones.
- Corrected score distributions applied.

## Top Recommendations
1. Review reported violations.
