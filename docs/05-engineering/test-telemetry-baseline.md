______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-29'

______________________________________________________________________

# Test Telemetry Baseline

Committed baseline for CI coverage and slow-test telemetry so engineering
audits do not depend only on ephemeral GitHub artifact retention.

## Baseline Snapshot

- Source branch: `main`
- Source commit: `pending`
- Source run id: `pending`
- Refresh status: `pending_initial_refresh`
- Refreshed at (UTC): `pending`

## Coverage

- Hard threshold: `85.0%`
- Actual coverage: `pending`
- Threshold satisfied: `None`

## Duration Telemetry

- Total collected test cases: `pending`

### Top Slowest Tests

No committed slow-test baseline is present yet. Refresh from a main-branch CI
run using `python -m scripts.engineering.ci.update_test_telemetry_baseline`.

## Refresh Procedure

1. Download `reports/coverage/coverage.xml` and
   `reports/test-telemetry/slowest-tests.json` from a main-branch CI run.
2. Run
   `python -m scripts.engineering.ci.update_test_telemetry_baseline --source-commit <sha> --source-run-id <run-id>`.
3. Commit the updated YAML and Markdown baseline together.
