## 2025-02-14 - Optimize deduplication uniqueness checks in Polars
**Learning:** When checking uniqueness of a subset of columns, `df.n_unique(subset=key_columns)` is significantly faster (around 25%) than materializing a projection with `df.select(key_columns).n_unique()` because it avoids creating the intermediate DataFrame.
**Action:** Use `subset=` arguments in `n_unique()` whenever possible to prevent unnecessary memory allocations and FFI overhead, especially in hot paths like pre-join deduplication.
