## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-24 - [PyArrow vs Pandas for List of Dicts]
**Learning:** Converting a list of dicts to PyArrow Table (`pa.Table.from_pylist`) is significantly slower (2x-5x) than converting to Pandas DataFrame (`pd.DataFrame.from_records`), especially with nested structures. PyArrow's type inference overhead is high.
**Action:** When validating with Pandera (pandas backend), do NOT convert to Arrow first if the goal is validation. Use `pd.DataFrame.from_records` instead of `pd.DataFrame()` constructor for a slight speedup (10-20%).
