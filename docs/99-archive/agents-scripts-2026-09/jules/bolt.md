Owner: @bioetl-platform
Status: archived
Class: archive
Original location: `.jules/bolt.md`

## 2023-10-24 - Polars Selectors are 3x faster than list comprehensions over df.columns
**Learning:** Polars list comprehensions over `df.columns` (e.g. `[col for col in df.columns if ...]`) and generating massive expression lists in Python (e.g. `[pl.col(c).is_not_null() for c in cols]`) create significant FFI overhead when crossing the Python/Rust boundary.
**Action:** Use native Polars selectors (e.g., `~cs.starts_with("_")` or `cs.by_name(cols)`) within dataframe operations like `.select()` or `pl.any_horizontal()`. This shifts the column identification entirely into Rust, providing a 3x speedup on wide dataframes.
