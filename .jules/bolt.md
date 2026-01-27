## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-24 - [Schema-Driven vs Dictionary Copy for PyArrow Preparation]
**Learning:** When preparing dictionaries for PyArrow `from_pylist`, creating a new dictionary by iterating only schema fields is significantly faster (~8x for records with many extra fields) than copying the original dictionary (via `dict.copy()` or comprehension) and relying on PyArrow to filter. This is because `dict.copy()` incurs overhead proportional to the total size of the dictionary, whereas schema-driven construction is proportional only to the output schema size.
**Action:** Use schema-driven iteration when transforming loose dictionaries (e.g., from API responses) into strict schemas, especially when the source data contains many unused fields.
