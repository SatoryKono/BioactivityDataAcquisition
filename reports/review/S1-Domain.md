# Code Review Report — S1: Domain
**Date**: 2026-03-24
**Scope**: src/bioetl/domain
**Files reviewed**: 350
**Total LOC**: 43236
**Status**: FAIL
**Score**: 0.0/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | - |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | - |
| DI Violations | 0 | 0 | 0 | 0 | 0 | - |
| Naming | 0 | 0 | 0 | 0 | 0 | - |
| Types | 321 | 0 | 0 | 0 | 0 | - |
| Testing | 0 | 0 | 0 | 0 | 0 | - |
| **TOTAL** | **321** | **0** | **319** | **0** | **2** | **0.0** |


## Critical Issues
None.

## High Issues
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/observability_contract.py:84`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def normalize_observability_context(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/observability_contract.py:145`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def enforce_observability_contract_context(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/observability_contract.py:217`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def normalize_observability_metric_labels(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/observability_contract.py:261`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def build_observability_contract_payload(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:47`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def serialize_to_json(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:85`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def serialize_to_json_canonical(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:115`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def deserialize_from_json(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:170`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _serialize_with_orjson(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:185`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _serialize_with_stdlib(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:202`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _deserialize_with_orjson(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/serialization.py:217`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _deserialize_with_stdlib(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context.py:38`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def create(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context.py:63`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def bind_logger(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/locking.py:100`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def create(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context_cached_bronze.py:23`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def from_options(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/normalization_authors.py:60`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def _try_parse_json_array(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context_filtering.py:43`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def from_csv(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context_filtering.py:74`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def from_ids(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/context_filtering.py:104`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def from_multi_ids(
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_aggregate.py:126`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def create(
  ```

## Medium Issues
None.

## Low Issues
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
