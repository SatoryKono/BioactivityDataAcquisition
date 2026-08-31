## 2024-10-24 - Avoid FFI overhead in dataframe schema iteration
**Learning:** Accessing `df[col].dtype` in a Python loop for many columns causes massive Python FFI overhead. Iterating over `df.schema.items()` natively leverages Polars structures and is much faster.
**Action:** Use `df.schema.items()` or `dict(zip(df.columns, map(str, df.dtypes)))` instead of looping through `df.columns` and accessing individual datatypes.

## 2024-10-24 - n_unique() vs unique().height
**Learning:** While `unique(maintain_order=False).height` can be faster for cardinality counts on large dataframes, replacing `n_unique()` forces the engine to materialize a new dataframe of unique rows in memory before calculating its length. This causes a severe memory regression and compute inefficiency, making `n_unique()` the computationally optimal path.
**Action:** Stick to `n_unique()` for simple unique row counts instead of `unique(maintain_order=False).height`.
