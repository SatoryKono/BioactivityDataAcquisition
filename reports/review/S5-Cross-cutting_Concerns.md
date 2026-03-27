# Code Review Report — S5: Cross-cutting Concerns
**Date**: 2026-03-24
**Scope**: src/bioetl
**Files reviewed**: 1258
**Total LOC**: 171190
**Status**: FAIL
**Score**: 0.0/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | - |
| Anti-Patterns | 3 | 0 | 0 | 0 | 0 | - |
| DI Violations | 0 | 0 | 0 | 0 | 0 | - |
| Naming | 0 | 0 | 0 | 0 | 0 | - |
| Types | 2107 | 0 | 0 | 0 | 0 | - |
| Testing | 0 | 0 | 0 | 0 | 0 | - |
| **TOTAL** | **2110** | **0** | **2106** | **0** | **4** | **0.0** |


## Critical Issues
None.

## High Issues
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/__init__.py:18`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _get_origin_with_union_fix(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/__init__.py:35`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _find_fn_by_subclass_or_union(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/__init__.py:64`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _dispatcher_call_with_any_fallback(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/observability.py:23`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def start_metrics_server(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/formatters.py:119`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def echo_quarantine_record(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/formatters.py:206`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _format_preview_row(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/__init__.py:31`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def create_pipeline_runner(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/registry_helpers.py:39`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _build_registered_registry(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:67`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _handle_export_failure(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:88`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _run_export_async(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:135`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _run_export_sync(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:200`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _build_export_options(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:215`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _run_preview(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:237`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _run_export(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py:262`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _list_tables_or_exit(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/debug.py:36`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def get_pipeline_runner_service(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/debug.py:75`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def debug(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/export.py:76`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def export_command(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/domains/composite/support.py:33`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def push_metrics_to_gateway(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/interfaces/cli/commands/domains/composite/support.py:43`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def emit_composite_startup(
  ```

## Medium Issues
None.

## Low Issues
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:65`
- **Description**: Any used without comment
- **Code**:
  ```python
  Implements LoggerPort protocol with signature: method(_event: str, **kwargs: Any)
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/__init__.py:94`
- **Description**: Any used without comment
- **Code**:
  ```python
  def __getattr__(name: str) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `src/bioetl/domain/normalization.py:51`
- **Description**: Any used without comment
- **Code**:
  ```python
  value: Any value to coerce to string. None returns None.
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `src/bioetl/domain/value_objects/dq_metrics_calculations.py:119`
- **Description**: Any used without comment
- **Code**:
  ```python
  value: Any value, including dicts and lists that are not natively hashable.
  ```

## Positive Observations
- The code is overall well-structured.

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Final | 100% | 10.0 | -10.0 | 0.0 |
