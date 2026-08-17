## 2025-03-09 - [Polars Performance: maintain_order=True]
**Learning:** Polars `maintain_order=True` is computationally expensive and causes FFI overhead for high-cardinality data compared to `maintain_order=False`.
**Action:** Replace `maintain_order=True` with `maintain_order=False` on `group_by` and `unique` if deterministic order is not strictly necessary, or apply explicit `.sort()` after if it is required.
