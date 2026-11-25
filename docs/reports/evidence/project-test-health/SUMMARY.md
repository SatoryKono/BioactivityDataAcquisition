---
status: active-non-canonical
last_verified: "2026-11-25"
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
workflows. The historical 2026-10-13 tracked inventory recorded 3,038
`test_*.py` files. A source-only census on tree `d5711c0c174871d60fe095383eae3ec1f628346e`
counts 3,051 files using `git ls-tree -r --name-only d5711c0c -- tests`
and filtering basenames matching `test_*.py`. This is an audited-tree annotation,
not a new test execution or coverage measurement; the 2026-10-08 capture remains historical. This summary
remains a non-canonical backlog signal and does
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

Re-verified on 2026-11-25 at source commit
`bf83a0cf5da2858c90722eff33c5a62341b9e353`: `git ls-tree -r --name-only bf83a0cf5da2858c90722eff33c5a62341b9e353 -- tests`
contains **3,413 tracked `test_*.py` modules** after filtering file basenames.
The three canonical configuration sources listed above remain present and readable.
This verification covers only `verification_scope: tracked_test_module_inventory`;
it records no new test execution, coverage measurement, or release admission.
The historical 2026-10-08 coverage capture and its remote artifact verification
dates remain unchanged.

The PR branch also recorded a source-only census at
`eed011c2eafb64694b184b99b4746e4a64abd25b`: 3,362 tracked `test_*.py`
modules under `tests/`, verified with `git ls-tree -r --name-only`.
This historical census records no test execution or coverage measurement.

Re-verified on 2026-11-17 at source commit
`f39053c1840173e49ed64eac8a3673f70bcf9eca`: `git ls-tree -r --name-only f39053c1840173e49ed64eac8a3673f70bcf9eca -- tests`
contains **3333 tracked `test_*.py` modules**. The three canonical configuration
sources listed above remain present and readable. This verification covers only
`verification_scope: tracked_test_module_inventory`; the date is not a new
test run, coverage measurement, or release/acceptance decision. The historical
2026-10-08 17-shard evidence and all prior outcomes below are unchanged; its
remote artifacts were not re-verified by this source census.

A separate source-only census on 2026-11-17 at commit
`4837b8207d1676a7c70a8627662e968e2409a212`: the canonical source list and historical shard manifest
remain present. The tracked tree contains 3,332 files with basenames
matching `test_*.py` under `tests/`, counted from
`git ls-files 'tests/**/test_*.py'`.
This inventory check records no test execution or coverage measurement.
The 2026-10-08 17-shard capture remains the latest measured coverage in this summary.

Re-verified on 2026-11-09 at source commit
`82b3d165d87bcb19c1d4214d9ccf7254750687b5`: the canonical source list and historical shard manifest
remain present. The tracked tree contains 3,238 files with basenames
matching `test_*.py` under `tests/`, counted from
`git ls-tree -r --name-only 82b3d165d87bcb19c1d4214d9ccf7254750687b5 -- tests`.
This inventory check records no test execution or coverage measurement.
The 2026-10-08 17-shard capture remains the latest measured coverage in this summary.

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
