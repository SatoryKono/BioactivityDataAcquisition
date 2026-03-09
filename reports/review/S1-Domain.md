# Code Review Report — S1: Domain
**Date**: 2024-03-09
**Scope**: src/bioetl/domain
**Files reviewed**: 364
**Total LOC**: 34249
**Status**: PASS
**Score**: 9.5/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 1 | 0 | 1 | 0 | 0 | 9.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 1 | 0 | 1 | 0 | 0 | 9.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |

## High Issues
### ARCH-002: structlog in Domain
- **Rule**: ARCH-002
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  src/bioetl/domain/context.py:        **kwargs: Any,  # Any: structlog-compatible key=value pairs
  src/bioetl/domain/context.py:            **kwargs: Key-value pairs to bind to the structured logger (structlog-compatible).
  src/bioetl/domain/ports/observability/logging.py:    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
  src/bioetl/domain/ports/observability/logging.py:    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
  src/bioetl/domain/ports/observability/logging.py:            Implementation-defined return value (structlog-compatible).
  ```
### DI-001: Hardcoded constructor instantiation
- **Rule**: DI-001
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  src/bioetl/domain/services/activity_aggregator/_aggregator_extensions.py:        result_conc = Concentration(
  src/bioetl/domain/services/unit_converter.py:        concentration = Concentration(value=value, unit=source_unit)
  src/bioetl/domain/entities/crossref.py:    doi: str = PydanticField(description="Digital Object Identifier (normalized)")
  src/bioetl/domain/entities/crossref.py:    title: str | None = PydanticField(default=None, description="Publication title")
  src/bioetl/domain/entities/crossref.py:    abstract: str | None = PydanticField(
  ```

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30% | 10 | -1.0 | 2.7 |
| Anti-Patterns | 25% | 10 | -0 | 2.5 |
| DI Violations | 20% | 10 | -1.0 | 1.8 |
| Naming | 10% | 10 | -0 | 1.0 |
| Types | 10% | 10 | -0 | 1.0 |
| Testing | 5% | 10 | -0 | 0.5 |
| **FINAL** | **100%** | | | **9.5** |
