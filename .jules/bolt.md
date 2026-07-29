## 2024-05-24 - Polars Boolean Mask Materialization Overhead
**Learning:** In the BioETL project, counting boolean mask matches in Polars DataFrames using `len(df.filter(expr))` introduces significant overhead by materializing a new filtered DataFrame in memory. This is particularly problematic in data quality checks that process large volumes of data.
**Action:** Instead of filtering, build a Polars expression and evaluate it using `int(df.select(expr.sum()).item())` to eliminate memory allocation and speed up execution, while satisfying `mypy` strict type-checking rules.
