# Code Review Report — S3: Infrastructure
**Date**: 2024-03-09
**Scope**: src/bioetl/infrastructure
**Files reviewed**: 287
**Total LOC**: 38186
**Status**: PASS
**Score**: 9.6/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Anti-Patterns | 1 | 0 | 1 | 0 | 0 | 9.0 |
| DI Violations | 1 | 0 | 1 | 0 | 0 | 9.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |

## High Issues
### ADR-014: datetime.now() in Infrastructure
- **Rule**: ADR-014
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  src/bioetl/infrastructure/storage/silver_writer.py:        started_at, start_perf = datetime.now(UTC), time.perf_counter()
  src/bioetl/infrastructure/storage/metadata_builder.py:        now = datetime.now(UTC)
  src/bioetl/infrastructure/storage/metadata_builder.py:        now = ingestion_ts or datetime.now(UTC)
  src/bioetl/infrastructure/storage/metadata_builder.py:        now = datetime.now(UTC)
  src/bioetl/infrastructure/adapters/common/api_request_collector.py:            timestamp=timestamp or datetime.now(UTC),
  ```
### DI-001: Hardcoded constructor instantiation
- **Rule**: DI-001
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  src/bioetl/infrastructure/export/dq_report_writer.py:        self._base_path = Path(base_path)
  src/bioetl/infrastructure/export/dq_report_writer.py:        self._serializer = DQReportSerializer()
  src/bioetl/infrastructure/export/dq_report_writer.py:                source_dir = Path(
  src/bioetl/infrastructure/export/dq_report_writer.py:            output_path = Path(output_path)
  src/bioetl/infrastructure/export/dq_report_writer.py:            output_path = Path(output_path)
  ```

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30% | 10 | -0 | 3.0 |
| Anti-Patterns | 25% | 10 | -1.0 | 2.2 |
| DI Violations | 20% | 10 | -1.0 | 1.8 |
| Naming | 10% | 10 | -0 | 1.0 |
| Types | 10% | 10 | -0 | 1.0 |
| Testing | 5% | 10 | -0 | 0.5 |
| **FINAL** | **100%** | | | **9.6** |
