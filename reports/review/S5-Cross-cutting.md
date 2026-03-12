# Code Review Report — S5: Cross-cutting
**Date**: 2026-03-12
**Scope**: src/bioetl
**Files reviewed**: 998
**Total LOC**: 150889
**Status**: PASS
**Score**: 9.00/10.0

---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 12 | 0 | 0 | 0 | 16 | 7.00 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.00 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.00 |
| Naming | 4 | 0 | 0 | 0 | 4 | 9.00 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.00 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.00 |
| **TOTAL** | **16** | **0** | **0** | **0** | **16** | **9.00** |

## Critical Issues (MUST fix before merge)
None

## High Issues
None

## Medium Issues
None

## Low Issues
### ARCH-000: Missing future annotations
- **File**: `src/bioetl/infrastructure/config_load_api.py:1`

### NAME-001: Class suffix missing
- **File**: `src/bioetl/infrastructure/adapters/health_check_mixin.py:50`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/infrastructure/schemas/silver_chembl.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/infrastructure/schemas/base_schemas.py:1`

### NAME-001: Class suffix missing
- **File**: `src/bioetl/infrastructure/storage/bronze_writer_side_effects_mixin.py:50`

### NAME-001: Class suffix missing
- **File**: `src/bioetl/infrastructure/storage/write_resilience.py:100`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/composition/services/metadata_assemblers.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/composition/services/metadata_coordinator.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/aggregates/quarantine_entry.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/aggregates/batch.py:1`

### NAME-001: Class suffix missing
- **File**: `src/bioetl/domain/composite/aggregation.py:100`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/models/metadata.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/value_objects/dq_report.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/value_objects/dq_report_results.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/value_objects/chemical.py:1`

### ARCH-000: Missing future annotations
- **File**: `src/bioetl/domain/services/_dq_serializer_html/_styles.py:1`


## Positive Observations
- Mechanically verified DI bindings and clean boundaries in large parts of the code.
- Types are primarily consistent.

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30.0% | 10 | 3.0 | 2.10 |
| Anti-Patterns | 25.0% | 10 | 0.0 | 2.50 |
| DI Violations | 20.0% | 10 | 0.0 | 2.00 |
| Naming | 10.0% | 10 | 1.0 | 0.90 |
| Types | 10.0% | 10 | 0.0 | 1.00 |
| Testing | 5.0% | 10 | 0.0 | 0.50 |
| **FINAL** | **100%** | | | **9.00** |
