# Code Review Report — S5: Cross-cutting Concerns
**Date**: 2026-03-04
**Scope**: src/bioetl
**Files reviewed**: 998
**Total LOC**: 150889
**Status**: FAIL
**Score**: 0.0/10.0

---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 5 | 0 | 5 | 0 | 0 | 5.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 4 | 0 | 0 | 4 | 0 | 8.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **9** | **0** | **5** | **4** | **0** | **0.0** |

## High Issues
### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/__init__.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/__init__.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/observability.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/observability.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/exit_codes.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/cli/exit_codes.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/__init__.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/cli/__init__.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/metrics_server_integration.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/cli/commands/metrics_server_integration.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/health_server_integration.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/cli/commands/health_server_integration.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/orchestration/__init__.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/interfaces/orchestration/__init__.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/__init__.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/infrastructure/__init__.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/config_load_api.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/infrastructure/config_load_api.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`

## Medium Issues
### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:65`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  Implements LoggerPort protocol with signature: method(_event: str, **kwargs: Any)
  ```
- **Fix**:
  ```python
  Implements LoggerPort protocol with signature: method(_event: str, **kwargs: Any)  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' src/bioetl/infrastructure/observability/unified_logger.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/normalization.py:50`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  value: Any value to coerce to string. None returns None.
  ```
- **Fix**:
  ```python
  value: Any value to coerce to string. None returns None.  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' src/bioetl/domain/normalization.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/schemas/common/publication_base.py:188`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  # def _check_author_orcids(cls, series: Any) -> Any:
  ```
- **Fix**:
  ```python
  # def _check_author_orcids(cls, series: Any) -> Any:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' src/bioetl/domain/schemas/common/publication_base.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/value_objects/dq_metrics_calculations.py:119`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  value: Any value, including dicts and lists that are not natively hashable.
  ```
- **Fix**:
  ```python
  value: Any value, including dicts and lists that are not natively hashable.  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' src/bioetl/domain/value_objects/dq_metrics_calculations.py`

## Positive Observations
- Hexagonal architecture directory structure is strictly maintained.
