# Step 8 — grafana-audit.regression

Candidate ≠ BASE: WORK_BRANCH unique JSON diffs vs `origin/main` `b38cf2d489`.

| Check | BASE | Candidate |
| --- | --- | --- |
| visual-semantics | FAIL 9104 | PASS |
| authored font floor | FAIL 9103=15px | PASS |
| inventory --check | PASS | PASS |
| perf budgets | PASS | PASS |
| scalar-density | PASS | PASS |

No FIT-004 JSON change (still #9340). grafana-six.reverify not used.
