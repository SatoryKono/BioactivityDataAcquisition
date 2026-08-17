## 2025-02-08 - Maintain Order in Polars Group By
**Learning:** In Polars, setting `maintain_order=True` in `group_by` and `unique` carries a significant performance penalty (sometimes 30%+ slowdown) compared to `maintain_order=False` followed by an explicit `sort()`.
**Action:** Always default to `maintain_order=False` for high-cardinality grouping and deduplication, and add `.sort()` explicitly if deterministic output order is required.

## 2023-10-24 - [Polars Vectorization for Loop Optimization]
**Learning:** Iterating over Polars DataFrames using `.filter(...).height` inside a Python loop creates massive FFI overhead.
**Action:** Replace these iterative patterns with vectorized expressions evaluated at once via `.select(...)` and extracting results using `.row(0, named=True)`.
