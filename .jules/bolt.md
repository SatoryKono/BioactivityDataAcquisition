## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-06-01 - [Optimizing List of Dicts Processing for Arrow]
**Learning:** When preparing a list of dictionaries for `pyarrow.Table.from_pylist`, avoid creating new dictionaries via list comprehensions just to filter keys. `from_pylist(..., schema=schema)` handles filtering efficiently in C++.
**Action:** Instead of `[{k: v for k, v in r.items() if k in schema} for r in records]`, pass the records directly to `from_pylist`. If partial modification (e.g., JSON serialization) is needed, use `r.copy()` and modify only necessary fields, which is ~3x faster than full dictionary reconstruction.
