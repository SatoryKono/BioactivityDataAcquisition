# Code Review Report — S6: Tests
**Date**: 2026-03-04
**Scope**: tests
**Files reviewed**: 862
**Total LOC**: 237537
**Status**: FAIL
**Score**: 0.0/10.0

---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 5 | 0 | 5 | 0 | 0 | 5.0 |
| Anti-Patterns | 5 | 0 | 0 | 5 | 0 | 7.5 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 5 | 0 | 0 | 5 | 0 | 7.5 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **15** | **0** | **5** | **10** | **0** | **0.0** |

## High Issues
### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/test_architecture.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/conftest.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/conftest.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/strategies.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/strategies.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/fakes/__init__.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/fakes/__init__.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_forbidden_imports.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_forbidden_imports.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_documentation.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_documentation.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_domain_purity.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_domain_purity.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_no_datetime_now_in_infrastructure.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_no_datetime_now_in_infrastructure.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_any_budget.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_any_budget.py`

### ARCH-000: Future Annotations
- **Rule**: ARCH-000 (Future Annotations)
- **Severity**: HIGH
- **File**: `tests/architecture/test_layer_dependencies.py:1`
- **Description**: Missing 'from __future__ import annotations'
- **Code**:
  ```python
  <missing>
  ```
- **Fix**:
  ```python
  from __future__ import annotations

  ```
- **Verification**: `grep -q 'from __future__ import annotations' tests/architecture/test_layer_dependencies.py`

## Medium Issues
### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `tests/test_architecture.py:523`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  """No print() or unsafe builtins."""
  ```
- **Fix**:
  ```python
  """No logger.info() or unsafe builtins."""
  ```
- **Verification**: `grep 'print(' tests/test_architecture.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/conftest.py:140`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  def isolated_registry() -> Any:
  ```
- **Fix**:
  ```python
  def isolated_registry() -> Any:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/conftest.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/conftest.py:148`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  def populated_isolated_registry(isolated_registry: Any) -> Any:
  ```
- **Fix**:
  ```python
  def populated_isolated_registry(isolated_registry: Any) -> Any:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/conftest.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/conftest.py:181`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  def query_ignore_email(request_1: Any, request_2: Any) -> bool:
  ```
- **Fix**:
  ```python
  def query_ignore_email(request_1: Any, request_2: Any) -> bool:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/conftest.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/conftest.py:192`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  ) -> Any:
  ```
- **Fix**:
  ```python
  ) -> Any:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/conftest.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/fakes/storage_fake.py:130`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  schema: Any,
  ```
- **Fix**:
  ```python
  schema: Any,  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/fakes/storage_fake.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_any_budget.py:1`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  """Architecture test: Any usage justification (TYPE-002).
  ```
- **Fix**:
  ```python
  """Architecture test: Any usage justification (TYPE-002).  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/architecture/test_any_budget.py`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_any_budget.py:128`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(f"\n[Any Budget] Unjustified: {count} / Threshold: {MAX_UNJUSTIFIED}")
  ```
- **Fix**:
  ```python
  logger.info(f"\n[Any Budget] Unjustified: {count} / Threshold: {MAX_UNJUSTIFIED}")
  ```
- **Verification**: `grep 'print(' tests/architecture/test_any_budget.py`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_antipatterns.py:108`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  assert not violations, "print() usage found:\n" + "\n".join(violations[:50])
  ```
- **Fix**:
  ```python
  assert not violations, "logger.info() usage found:\n" + "\n".join(violations[:50])
  ```
- **Verification**: `grep 'print(' tests/architecture/test_antipatterns.py`

### TYPE-002: Any Usage
- **Rule**: TYPE-002 (Any Usage)
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_config_ci_invariants.py:173`
- **Description**: Usage of Any without justification
- **Code**:
  ```python
  def _deep_string_search(obj: Any, fragment: str) -> bool:
  ```
- **Fix**:
  ```python
  def _deep_string_search(obj: Any, fragment: str) -> bool:  # Any: justified because ...
  ```
- **Verification**: `grep 'Any' tests/architecture/test_config_ci_invariants.py`

## Positive Observations
- Hexagonal architecture directory structure is strictly maintained.
