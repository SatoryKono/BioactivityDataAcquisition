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
