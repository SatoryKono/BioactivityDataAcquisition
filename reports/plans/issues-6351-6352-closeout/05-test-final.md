# Final validation: issues #6351 and #6352

Date: 2026-07-19

## Acceptance checks

All of the following completed with exit code 0:

- `report-module-coverage --check --allow-missing-coverage-xml`
- `report-family-baseline --check`
- `report-dead-code-inventory --check`
- `report-compatibility-importer-census --check`
- `generate_compatibility_facade_snapshot.py --check`
- `report-domain-io-taint-inventory --check`
- `report_test_governance_audit --json-out reports/quality/test-governance-current.json`
- `report_test_governance_audit --check`
- `report-flaky-test-burndown-review --check`
- `report-debt-governance-gates --check --changed-from-ref refs/remotes/origin/main`
- `report-architecture-debt-remote-main-baseline --check`
- `ruff check` and `ruff format --check` for changed Python surfaces
- JSON/YAML parsing for all changed structured artifacts
- `git diff --check`

## Focused tests

- Impacted producer, debt-rollup, compatibility, drift-check, and architecture
  group: 140 passed, 13 skipped.
- Earlier retained-entrypoint governance regression group: 46 passed.
- The #6022-#6028 reconstructed evidence-node tests are included in the
  impacted group and all 8 passed.

The WSL skips are the repository's explicit filesystem-performance skips for
importer-census and source-tree hash scans; their deterministic CLI equivalents
were run directly and passed.

## Skipped validation

- Full provider/VCR replay and the repo-wide coverage lane were not run because
  these changes do not alter provider or `src/bioetl` runtime behavior.
- The complete test matrix was left to the PR's GitHub Actions checks; local
  validation used the directly impacted producer and architecture surfaces.
- The plain debt-rollup check without `--changed-from-ref` was not used as a PR
  acceptance signal because it intentionally builds a different payload from
  the canonical CI command in `.github/workflows/tests.yml`.
