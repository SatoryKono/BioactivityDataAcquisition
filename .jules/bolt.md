## 2024-05-18 - [Avoid materializing DataFrames for uniqueness counting]
**Learning:** Using `.unique(maintain_order=False).height` to count unique rows forces Polars to materialize a new DataFrame in memory, which can cause severe memory regressions and compute inefficiency on large datasets.
**Action:** Always use `.select(keys).n_unique()` when only the count of unique combinations is needed, to avoid allocating a new DataFrame.
