## 2026-08-25 - Polars Python Loop Overheads
**Learning:** Iterating over `df.columns` to access column types with `df[col].dtype` creates huge FFI overhead in Polars compared to using `df.dtypes` and zip, or using Polars selectors `cs.by_dtype()`.
**Action:** Always prefer `df.dtypes` or Polars selectors like `cs.by_dtype()` over python for loops when filtering or reading schemas.
