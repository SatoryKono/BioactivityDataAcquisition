## 2024-05-15 - [Initial]
**Learning:** Initializing bolt journal.
**Action:** Keep learning and tracking performance issues.

## 2024-05-15 - [Loop Aggregate Optimization]
**Learning:** Accumulating aggregates line-by-line in a Python loop is slower than using Python's native `sum()` function over a dictionary's `.values()` or using basic multiplication.
**Action:** Extract aggregations outside the loop to avoid Python execution overhead when profiling dataframes.
