# [test] Resolve Legacy Validation Test Debt Markers

**Status**: completed_in_repo
**Priority**: P2 (Medium)
**Labels**: `dq`, `testing`, `architecture`, `validation`
**Epic**: Architecture Validation Debt Remediation 2026Q3
**Last audited**: 2026-05-29

## Problem

`tests/architecture/test_validation_test_debt_markers.py` currently enforces three
legacy TODO markers in validation suites:

- `tests/integration/validation/test_external_verification.py`
- `tests/unit/application/services/dq/test_structural_validation.py`
- `tests/unit/application/services/dq/test_logical_validation.py`

These markers indicate intentionally incomplete validation coverage and make the
test suite state opaque at architecture review time.

## Evidence

- `tests/architecture/test_validation_test_debt_markers.py`
- `tests/integration/validation/test_external_verification.py`
- `tests/unit/application/services/dq/test_structural_validation.py`
- `tests/unit/application/services/dq/test_logical_validation.py`

## Required Outcome

- Remove the legacy TODO markers and close the explicit debt references.
- Add enough structural and logical DQ tests to justify current test coverage.
- Expand external verification coverage where practical and document any bounded
  remaining gaps.

## Implementation Plan

1. Open each flagged file and quantify currently covered scenarios against the
   debt comment text.
2. Add missing external verification cases for currently untested positive and
    negative ID verification paths.
3. Extend structural DQ tests with additional boundary and threshold coverage.
4. Extend logical DQ tests with additional severity/rule-combination coverage.
5. Keep `test_no_legacy_validation_test_debt_markers` updated and green.
6. Re-run targeted and architecture-level DQ validation suites.

## Completion Update (2026-05-29)

- Legacy marker checks were already not present as raw TODO strings in the three target
  validation suites.
- Added additional covered cases for:
  - `tests/integration/validation/test_external_verification.py`:
    - unsupported entity-type raises
    - unsupported filter field logs warning
  - `tests/unit/application/services/dq/test_structural_validation.py`:
    - unparseable FK mapping keys are ignored
    - SCD integrity defaults to pass when business key is missing
  - `tests/unit/application/services/dq/test_logical_validation.py`:
    - combined warn+error rule failures produce error-first severity
    - rules with missing columns are treated as pass

## Suggested File Targets

- `tests/architecture/test_validation_test_debt_markers.py`
- `tests/integration/validation/test_external_verification.py`
- `tests/unit/application/services/dq/test_structural_validation.py`
- `tests/unit/application/services/dq/test_logical_validation.py`

## Done When

- No legacy test-debt TODO markers remain in the flagged files.
- Architecture debt marker test passes.
- Added tests are executed and pass with existing DQ and integration suites.
