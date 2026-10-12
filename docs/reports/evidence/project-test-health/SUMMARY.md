---
status: active-non-canonical
last_verified: "2026-10-08"
freshness_window_days: 7
owner: quality
canonical_sources:
  - configs/quality/test_matrix.yaml
  - configs/quality/test_health_reporting.yaml
  - configs/quality/fixture_governance_ledger.yaml
allowed_interpretation: backlog_signal_only
verification_scope: tracked_test_module_inventory
---

# Project Test Health

## Current status

On 2026-10-08, CircleCI run [17286](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/17286)
completed the canonical 17-shard coverage plan for source commit
`ceedc671b613ec3c2b25bbbae86b8b950719ddb6` on
`fix/cf-wave1-pagination-vcr-security`. Its complete manifest binds source
tree `3cabab41baf177eb6f34163e59cbdb352e4cbbb8d570d3af7551bf66790c7714` and
test tree `ad43e49af046f215efd16b0b4d629bc452fa1729da73c47e6ec00e48cee800b4`.
All 17 JUnit inputs report 33,424 passed, 175 skipped, and 0 failed; combined
coverage is 99.68% line and 94.29% branch. The portable manifest records the
public CircleCI artifact index, raw manifest path and SHA-256, and SHA-256 for
every JUnit and coverage input; those bindings were re-verified from run 17286
on 2026-10-10. The committed telemetry baseline separately retains GitHub PR
workflow [37743490942](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/37743490942)
for the same source commit as a `historical_unverified_ci_binding`; that entry
is not used as provenance for this CircleCI capture.

This evidence covers the canonical 17-shard plan, not every repository test
surface. The manifest excludes architecture, performance, manual E2E,
live-provider contracts, and memory selectors; those gates have separate
workflows. The tracked test-module inventory contains 3,033 `test_*.py` files
as of 2026-10-08. This summary remains a non-canonical backlog signal and does
not claim lifecycle or release admission.

## Historical backlog signals

The earlier GR-DB-CORR broad attempt executed 29,758 tests with 10 failures
and 91 skips; a subsequent integration and affected-runner attempt executed
2,885 tests with three failures and 12 skips. The 108-test recheck of the
affected integration files passed. The architectural campaign then encountered
drift and a timeout. These historical attempts were not PASS results.

Older action items remain backlog signals and have not been re-audited by this
coverage refresh:

1. Complete remaining lifecycle, contract, and UTC metadata tests.
2. Add security regression coverage for HTML output and recursive redaction.

## Freshness note

Re-verified on 2026-10-08 against source HEAD
`ceedc671b613ec3c2b25bbbae86b8b950719ddb6`. The manifest is complete, all 17
required shard selections are present, and its test-tree hash matches the
working tree. Local evidence at
`reports/local/nav-tests-20260914/final-tests.xml` (1,199 passed, 11 skipped)
remains historical. Recurrence of #7419 remains a backlog signal.

This is a non-canonical repo-only evidence layer. The canonical sources of truth are:
- `configs/quality/test_matrix.yaml`
- `configs/quality/test_health_reporting.yaml`
- `configs/quality/fixture_governance_ledger.yaml`

This summary provides a backlog signal only and must be rebalanced with fresh evidence-pack rebaseline after any significant test campaign or infrastructure change.
