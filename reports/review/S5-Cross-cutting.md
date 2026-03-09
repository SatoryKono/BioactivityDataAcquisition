# Code Review Report — S5: Cross-cutting
**Date**: 2024-03-09
**Scope**: src/bioetl
**Files reviewed**: 1011
**Total LOC**: 124468
**Status**: PASS
**Score**: 9.8/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 1 | 0 | 1 | 0 | 0 | 9.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |

## High Issues
### DI-001: Hardcoded constructor instantiation
- **Rule**: DI-001
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  src/bioetl/domain/services/activity_aggregator/_aggregator_extensions.py:        result_conc = Concentration(
  src/bioetl/domain/services/unit_converter.py:        concentration = Concentration(value=value, unit=source_unit)
  src/bioetl/application/services/dq_report_service.py:        result = DQReportResult(
  src/bioetl/application/services/metadata_assemblers_helpers.py:    dq_summary = DQSummary(total_records=record_count, valid_records=record_count)
  src/bioetl/application/services/medallion_lifecycle.py:        result = ClearResult(
  ```

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30% | 10 | -0 | 3.0 |
| Anti-Patterns | 25% | 10 | -0 | 2.5 |
| DI Violations | 20% | 10 | -1.0 | 1.8 |
| Naming | 10% | 10 | -0 | 1.0 |
| Types | 10% | 10 | -0 | 1.0 |
| Testing | 5% | 10 | -0 | 0.5 |
| **FINAL** | **100%** | | | **9.8** |
