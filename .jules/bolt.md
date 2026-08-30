## 2025-02-24 - Optimize unique() height and vectorize n_unique()
**Learning:** In Polars, checking `.unique().height` maintains order by default which carries a massive performance penalty. Vectorizing operations across columns using `df.select([...]).row(0, named=True)` avoids huge Python FFI overhead compared to iterating via `df.columns` in Python loop.
**Action:** Always use `maintain_order=False` when the deterministic order isn't required and vectorize column checks using `df.select` instead of looping column operations in Python.
