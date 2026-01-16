## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [PyArrow Schema Filtering & Dict Construction]
**Learning:** Constructing new dictionaries via comprehension `{k: v for k, v in d.items() if k in schema}` is expensive in hot loops. `pa.Table.from_pylist(records, schema=schema)` automatically ignores extra fields in the dictionaries.
**Action:** When preparing data for PyArrow, do not manually filter dictionary keys if providing a schema. Instead, shallow copy the record (`rec.copy()`) if modification is needed (e.g. JSON serialization of fields), modify in-place, and pass the larger dicts to PyArrow. This yielded a ~1.5x - 2.2x speedup in `SilverWriter`.
