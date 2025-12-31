# Test Coverage Report Summary

**Date:** 2025-12-31
**Total Coverage:** 90.07%
**Coverage Threshold:** 85% (PASSED)

## Test Results

| Metric | Value |
|--------|-------|
| Total Tests | 4,413 |
| Passed | 4,376 |
| Failed | 3 |
| Skipped | 34 |

## Coverage by Layer

| Layer | Coverage |
|-------|----------|
| domain/ | ~95% |
| application/ | ~90% |
| infrastructure/ | ~85% |
| composition/ | ~92% |
| interfaces/ | ~88% |

## Failed Tests (E2E)

3 E2E tests failed due to pipeline chain issues:
- `test_chembl_target_then_activity_chain`
- `test_chembl_molecule_then_activity_chain`
- `test_all_chembl_pipelines_chain`

## Skipped Tests

- 30 contract tests (Live API tests disabled)
- 2 tests requiring psutil
- 2 tests requiring OpenTelemetry

## Generated Reports

| Report | Path |
|--------|------|
| HTML Report | `coverage_html/index.html` |
| XML Report | `coverage.xml` |
| Text Report | `coverage_report.txt` |

## Low Coverage Files (< 70%)

| File | Coverage |
|------|----------|
| `infrastructure/adapters/pubmed/pubmed_client.py` | 62.44% |
| `infrastructure/adapters/crossref/client.py` | 57.26% |
| `domain/ports/observability.py` | 61.90% |
| `domain/ports/storage.py` | 60.61% |

These are primarily Protocol definitions and edge-case error handling paths.
