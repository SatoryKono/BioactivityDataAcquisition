---
status: active-non-canonical
last_verified: "2026-09-22"
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

The tracked inventory contains 2625 test modules, counted from tracked
`tests/**/test_*.py` files on 2026-09-22. The GR-DB-CORR broad attempt executed
29,758 tests with 10 failures and 91 skips; it was not a PASS. A subsequent
integration and affected-runner attempt executed 2885 tests with three failures
and 12 skips. After fixes, the 108-test recheck of the affected integration
files passed. The architectural campaign encountered additional drift and a
timeout and remains incomplete. These local results do not establish CI,
release acceptance, or the health of the complete repository suite.

## Required evidence refresh

- Run the targeted unit suites for changed domain and application modules.
- Run `tests/architecture/` and record failures without weakening guards.
- Refresh module coverage inventory after source changes.
- Record skip/xfail counts and VCR freshness results.

## Open action items

1. Complete remaining lifecycle, contract, and UTC metadata tests.
2. Add security regression coverage for HTML output and recursive redaction.
3. Refresh this summary from the next full pytest telemetry artifact.

## Freshness note

Re-verified on 2026-09-14 against source HEAD
`5c4243c9adad87f4a8eb4a6b0228e4b65841810e` plus the local test repairs:
all three canonical source paths exist, and `git ls-files tests` contains 2436
Python modules named `test_*.py`. The scoped campaign selected tracked test
paths containing `dashboard` or `grafana`; its local JUnit receipt is
`reports/local/nav-tests-20260914/final-tests.xml` (1199 passed, 11 skipped).
Interpretation remains backlog signal only. No full-suite or new coverage
measurement is claimed. Recurrence of #7419.

This is a non-canonical repo-only evidence layer. The canonical sources of truth are:
- `configs/quality/test_matrix.yaml`
- `configs/quality/test_health_reporting.yaml`
- `configs/quality/fixture_governance_ledger.yaml`

This summary provides a backlog signal only and must be rebalanced with fresh evidence-pack rebaseline after any significant test campaign or infrastructure change.
