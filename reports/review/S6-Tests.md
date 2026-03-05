# Code Review Report — S6: Tests
**Date**: 2026-03-05
**Scope**: tests/
**Files reviewed**: 757
**Total LOC**: 222242
**Status**: WARN
**Score**: 7.5/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| ARCH | 0 | 0 | 0 | 0 | 0 | 10.0 |
| AP | 25 | 9 | 0 | 0 | 16 | 0.0 |
| DI | 0 | 0 | 0 | 0 | 0 | 10.0 |
| NAME | 0 | 0 | 0 | 0 | 0 | 10.0 |
| TYPE | 0 | 0 | 0 | 0 | 0 | 10.0 |
| TEST | 0 | 0 | 0 | 0 | 0 | 10.0 |

## Critical Issues
### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/infrastructure/factories/test_data_sources.py:38`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  "uniprot", http_client=mock_http_client, logger=mock_logger, api_key="test_key"
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/test_adapters.py:213`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  http_client=http_client, logger=mock_logger, api_key="test_key"
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py:45`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  api_key="test-api-key",
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py:171`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  api_key="test-api-key",
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/uniprot/test_uniprot_client_coverage.py:401`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  api_key="secret",
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/providers/test_registration_data_sources.py:223`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  pipeline_config.source.api_key = "${BIOETL_PUBMED_API_KEY}"
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/test_http_client_factory.py:98`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  settings = SimpleNamespace(pubmed_api_key="non-empty")
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/test_http_client_factory.py:112`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  settings = SimpleNamespace(pubmed_api_key="key", empty_value="", zero_value=0)
  ```

### AP-005: Hardcoded secret
- **Severity**: CRITICAL
- **File**: `tests/unit/domain/configs/test_base_configs.py:116`
- **Description**: Found hardcoded secret/credential
- **Code**:
  ```python
  api_key="secret-key",
  ```


## High Issues
None found.

## Medium Issues
None found.

## Low Issues
### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/test_architecture.py:523`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  """No print() or unsafe builtins."""
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_any_budget.py:128`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  print(f"\n[Any Budget] Unjustified: {count} / Threshold: {MAX_UNJUSTIFIED}")
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_antipatterns.py:109`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  assert not violations, "print() usage found:\n" + "\n".join(violations[:50])
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:1`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  """Architecture test: no print() in docstring examples in non-domain layers.
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:4`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  MUST use LoggerPort in docstring examples instead of print().
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:7`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  return values with print() in Python doctests.
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:9`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  See CLAUDE.md §11 Anti-Patterns: ❌ `print()` → `structlog` с `run_id`
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:28`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  # Pattern to detect print() calls in docstrings
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:29`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  # Matches: print(, print (, but not logger.print or _print
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:68`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  """Check for print() in docstring examples in a directory.
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:90`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  # Check if docstring contains Example: section with print()
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:96`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  f"{rel_path}:{lineno + i}: print() in docstring example"
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:114`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  structured logging patterns, not print() statements.
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:117`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  show return values with print() in Python doctests.
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:122`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  f"print() in docstring examples found in {layer_dir.name} layer:\n"
  ```

### AP-006: Print statement found
- **Severity**: LOW
- **File**: `tests/architecture/test_no_print_in_docstrings.py:124`
- **Description**: Found print() instead of unified logger
- **Code**:
  ```python
  + "\n\nUse logger.info/debug/warning/error instead of print()."
  ```


## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| ARCH | 30% | 10.0 | -0.00 | 3.00 |
| AP | 25% | 10.0 | -10.00 | 0.00 |
| DI | 20% | 10.0 | -0.00 | 2.00 |
| NAME | 10% | 10.0 | -0.00 | 1.00 |
| TYPE | 10% | 10.0 | -0.00 | 1.00 |
| TEST | 5% | 10.0 | -0.00 | 0.50 |
| **FINAL** | **100%** | | | **7.5** |
