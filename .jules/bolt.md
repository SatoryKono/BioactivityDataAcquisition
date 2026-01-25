## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [Redundant Python-side Schema Filtering]
**Learning:** `pa.Table.from_pylist(records, schema=schema)` implicitly ignores keys in `records` that are not in `schema`. Manually filtering dictionaries in Python before passing them to PyArrow is redundant and O(N*M) expensive.
**Action:** When preparing data for Arrow, rely on the `schema` argument for filtering. If transformations are needed (e.g., JSON serialization of complex fields), iterate only over the specific fields that need transformation on a shallow copy of the record, rather than rebuilding the entire dictionary. This yielded ~1.8x speedup.
