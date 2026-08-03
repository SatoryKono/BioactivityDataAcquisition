---
title: "[TEST-AUDIT] Publish branch-consumable test telemetry summaries for audits"
github_issue: 5434
labels: enhancement, ci, technical-debt
assignees: []
---

## Context

The CI workflow already generates JUnit telemetry, coverage combine, and
`slowest-tests.md/json`, but these artifacts are not consistently available as
branch-consumable repository surfaces for later audits.

## Problem

- Audit consumers can see the workflow definition, but not always the latest
  committed or branch-attached telemetry rollups.
- Coverage is measurable from committed artifacts today, but slow-test ranking
  is not reliably visible from a plain repository snapshot.
- This weakens repeatable auditability outside the live CI UI.

## Evidence

- `.github/workflows/tests.yml`
- `reports/coverage/coverage.xml`
- absence of committed `reports/test-telemetry/slowest-tests.*`

## Proposed Solution

1. Decide which telemetry artifacts should become branch-consumable surfaces.
2. Publish stable rollups for:
   - repo-level coverage summary
   - slowest tests
   - lane-level JUnit summaries
3. Keep heavy raw artifacts optional, but make the summary layer queryable from
   the repository snapshot.

## Acceptance Criteria

- [ ] Slow-test summary becomes available as a stable branch-consumable artifact
- [ ] Coverage summary remains easy to extract from committed or exported data
- [ ] Audit consumers can inspect test telemetry without opening the CI UI

## Validation

```bash
rg -n "slowest-tests\\.md|slowest-tests\\.json|coverage combine|summarize-junit" \
  .github/workflows/tests.yml
find reports/test-telemetry -maxdepth 2 -type f
```

## Risks

- Over-committing telemetry can create noise or artifact churn.
- The summary layer should stay lightweight and not duplicate raw CI storage.
