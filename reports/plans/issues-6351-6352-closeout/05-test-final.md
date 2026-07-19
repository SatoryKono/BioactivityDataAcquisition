# Final validation: issues #6351 and #6352

Date: 2026-07-18

## Acceptance checks

All of the following completed with exit code 0:

- `report-module-coverage --check --allow-missing-coverage-xml`
- `report-family-baseline --check`
- `report-dead-code-inventory --check`
- `report-compatibility-importer-census --check`
- `generate_compatibility_facade_snapshot.py --check`
- `report-domain-io-taint-inventory --check`
- `report_test_governance_audit --check`
- `report-flaky-test-burndown-review --check`
- `report-debt-governance-gates --check`
- `report-debt-governance-gates --check --changed-from-ref refs/remotes/origin/main`
- `report-architecture-debt-remote-main-baseline --check`
- `ruff check` and `ruff format --check` for changed Python surfaces
- `git diff --check`

## Focused tests

- Evidence/compatibility/Grafana/drift-check group: 136 passed, 12 skipped.
- #6022-#6028 reconstructed evidence node: 8 passed.
- Architecture quality/debt workflow group: 74 passed, 1 skipped.
- Earlier rollup and importer-census regression group: 115 passed, 13 skipped.

The WSL skips are the repository's explicit filesystem-performance skips for
importer-census and source-tree hash scans; their deterministic CLI equivalents
were run directly and passed.

## Broader baseline audit

The non-slow `tests/architecture` tree was also sampled from the clean
`origin/main` worktree with `--maxfail=50`. It reached 73% and stopped at 50
failures. These failures are pre-existing main-branch baseline problems outside
#6351/#6352, dominated by missing ignored historical closeout reports, stale
documentation/config generators, and unrelated Docker/domain/observability
contracts. The #6351/#6352 acceptance commands and focused tests listed above
remain green.

## Skipped validation

- Full provider/VCR replay and the repo-wide coverage lane were not run because
  these changes do not alter provider or `src/bioetl` runtime behavior.
- The full architecture tree cannot currently be a green closeout signal until
  its unrelated main-branch missing-artifact backlog is repaired.
