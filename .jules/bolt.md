## 2024-05-20 - Faster Subset n_unique in Polars
**Learning:** Despite the intermediate projection, `df.select(keys).unique(maintain_order=False).height` is significantly faster than `df.n_unique(subset=keys)` (or `df.select(keys).n_unique()`) for determining the number of unique combinations across multiple columns.
**Action:** Default to `select(keys).unique(maintain_order=False).height` when checking subset uniqueness to improve performance.
