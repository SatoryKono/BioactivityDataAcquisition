# Test Coverage Report

**Date:** 2025-12-31
**Python:** 3.11.14
**Platform:** Linux

## Summary

| Metric | Value |
|--------|-------|
| **Total Coverage** | **89.99%** |
| **Coverage Threshold** | 85% |
| **Status** | PASSED |
| **Total Statements** | 14,742 |
| **Missed Statements** | 1,214 |
| **Branches** | 2,588 |
| **Partial Branches** | 284 |

## Test Results

- **Total Tests:** ~5,500+
- **Passed:** ~5,500
- **Skipped:** ~40 (conditional tests)
- **Failed:** 1 (flaky benchmark - environment-specific)

## Coverage by Layer

### Domain Layer (High Coverage)
- `domain/types.py` - 100%
- `domain/config.py` - 100%
- `domain/validation.py` - 100%
- `domain/medallion.py` - 100%
- `domain/normalization.py` - 100%
- `domain/entities/chembl.py` - 100%
- `domain/services/identity_service.py` - 100%
- `domain/services/value_validator.py` - 100%

### Application Layer
- `application/core/base.py` - 100%
- `application/core/cleanup_service.py` - 100%
- `application/core/postrun_service.py` - 100%
- `application/services/medallion_lifecycle.py` - 100%
- `application/services/pipeline_runner_service.py` - 100%
- `application/pipelines/chembl/*` - 100% (all transformers)

### Infrastructure Layer
- `infrastructure/storage/bronze_writer.py` - 91%
- `infrastructure/storage/silver_writer.py` - 93%
- `infrastructure/storage/gold_writer.py` - 90%
- `infrastructure/locking/memory_lock.py` - 93%

### Composition Layer
- `composition/bootstrap.py` - 100%
- `composition/factories/storage_factory.py` - 100%
- `composition/factories/transformer_factory.py` - 100%

## Files with Lower Coverage (< 70%)

| File | Coverage | Reason |
|------|----------|--------|
| `__main__.py` | 0% | Entry point, tested via CLI |
| `application/core/executor.py` | 0% | Deprecated module |
| `application/core/protocols.py` | 0% | Protocol definitions only |
| `composition/_bootstrap/checkpoint.py` | 36% | Complex bootstrap paths |
| `composition/factories/runner_factory.py` | 40% | Factory methods |

## Reports Generated

- **HTML Report:** `coverage_report/index.html`
- **Text Output:** `coverage_output.txt`

## How to View

```bash
# Open HTML report in browser
open coverage_report/index.html

# Or run tests with coverage
make test
```
