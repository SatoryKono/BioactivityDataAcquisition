## 2025-03-09 - [Polars Performance: maintain_order=True]
**Learning:** Polars `maintain_order=True` is computationally expensive and causes FFI overhead for high-cardinality data compared to `maintain_order=False`.
**Action:** Replace `maintain_order=True` with `maintain_order=False` on `group_by` and `unique` if deterministic order is not strictly necessary, or apply explicit `.sort()` after if it is required.

## 2026-03-24 - Faster Deterministic Unique Sampling in Polars
**Learning:** In Polars, `unique(maintain_order=True)` incurs a significant performance penalty compared to `unique(maintain_order=False)`. For operations like bounded sampling where determinism is required, `unique(maintain_order=False).sort()` is measurably faster than `unique(maintain_order=True)`.
**Action:** Default to `maintain_order=False` for high-cardinality data. If deterministic order is needed, append an explicit `.sort()` instead of relying on `maintain_order=True`.
