# Implementation streams — CR-FULL 20260816

Exclusive stream for accepted (`confirm`) findings from the first five
successful leaves. Phase-5 product implementation is #8863.

| Stream | Issue | Findings | Priority | Scope |
|---|---:|---:|---|---|
| `domain-20260816-five-leaves` | #8863 | 32 | P1 | `{'critical': 1, 'major': 17, 'minor': 13, 'trivial': 1}` |

## Ordering recommendation

1. Critical `behavior-051` (`validate_composite` deep-preflight fail-closed).
2. Aggregates `aggregates-014` (`seal_with_counts` vs `mark_committed`).
3. Remaining behavior / composite / config / contracts confirms, one root
   cause per task.

Do not reopen #8643 / #8644 / #8645 / #8652 unless a confirm is a proven
regression. Do not implement the 82 rejected findings from these leaves.

Exact-cover of still-blocked CodeRabbit leaves remains #8859.

| domain-20260816-types-criticals | #8893 | 2 | P1 | types-018 semver pad/trim; types-022 single-mode defaults |
| domain-20260816-identity-json | #8891 | 8 | P1 | residual-root-006/028/029 + normalization-012/013/039/070/071 |
| domain-20260816-freeze-catalogs | #8888 | 3 | P1 | residual-root-011/012 + run_reports-002 |
| domain-20260816-run-report-accounting | #8889 | 4 | P1 | run_reports-005/011/013/014 |
| later-leaf-ok-triage | #8890 | ~756 raw | P2 | independent triage; types criticals promoted to #8893 |
| domain-20260816-types-remaining | #8895 | 13 | P1 | remaining types confirms after #8893 |
| domain-20260816-run-report-accounting | #8889 | 4 | P1 | run_reports-005/011/013/014 |
| later-leaf-ok-triage | #8890 | ~756 raw | P2 | independent triage; types criticals promoted to #8893 |
| domain-20260816-types-remaining | #8895 | 13 | P1 | remaining types confirms after #8893 |
| domain-20260816-vo-schemas | #8905 | 24 | P1 | VO fail-closed/freeze + schema date/dups/json/accession |
