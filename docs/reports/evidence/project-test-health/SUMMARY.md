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

The tracked inventory contains 3034 test modules, counted from tracked
`tests/**/test_*.py` files on 2026-10-08. A complete local
`run_local_coverage_verify` campaign on source commit
`3e734a6b872fff524c663cf183ade40aafdaea12` completed all 17 required shards:
33,599 tests, 0 failures, 0 errors, and 203 skips. Combined coverage was
99.68% line and 94.26% branch; both 85% gates passed. The manifest records
`source_tree_sha256=20f951f3aa0d2f535a757dca96af0b213f675f0fd74873f80d8c3feded56293c`.
This is local single-host evidence, not CI PASS, release acceptance, or proof
that the separate architecture campaign is complete.

Historical incomplete campaigns: the GR-DB-CORR broad attempt executed 29,758
tests with 10 failures and 91 skips; a subsequent integration and
affected-runner attempt executed 2885 tests with three failures and 12 skips.
The 108-test recheck of affected integration files passed. Those results are
retained as historical context and are superseded by the 2026-10-08 local
coverage measurement where their selections overlap.

## Required evidence refresh

- Run `tests/architecture/` and record its result without weakening guards.
- Check VCR freshness as a separate acceptance surface.
- Re-run the complete local 17-shard measurement after any later source-tree change.

## Open action items

1. Close the separate architecture campaign on the exact candidate SHA.
2. Record VCR freshness independently of the local coverage result.

## Freshness note

Re-verified on 2026-10-08 against source commit
`3e734a6b872fff524c663cf183ade40aafdaea12`: all canonical source paths exist,
the tracked test-module inventory is 3034, and the complete 17-shard local
manifest is bound to the source hash above. Interpretation remains backlog
signal only. The local run does not establish CI admission, release acceptance,
or architecture/VCR closeout.

This is a non-canonical repo-only evidence layer. The canonical sources of truth are:
- `configs/quality/test_matrix.yaml`
- `configs/quality/test_health_reporting.yaml`
- `configs/quality/fixture_governance_ledger.yaml`

This summary provides a backlog signal only and must be rebalanced with fresh evidence-pack rebaseline after any significant test campaign or infrastructure change.
