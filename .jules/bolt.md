## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [Schema Introspection and Dict Filtering]
**Learning:** Repeatedly calling `schema.to_schema()` (Pandera) inside a loop is expensive due to object creation and introspection. Caching the result yields significant savings. Additionally, filtering dictionaries in-place by deleting keys (`del r[k]`) is ~60% faster than creating new dictionaries via comprehension, especially when most keys are kept.
**Action:** Cache schema definitions in `__init__`. Use in-place modification for transient record batches when filtering fields.
