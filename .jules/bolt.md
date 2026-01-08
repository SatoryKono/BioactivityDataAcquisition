## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-24 - [Pandera Schema Conversion Overhead]
**Learning:** `pandera.DataFrameModel.to_schema()` is an extremely expensive operation (invokes type inspection and object creation). Calling this inside a hot loop (e.g., inside `write_gold` for every batch) caused massive slowdowns (~0.07s per call vs 7µs cached).
**Action:** Always pre-calculate/convert schemas to their runtime representation (e.g., column sets) in `__init__` if they are static. Never call `to_schema()` inside data processing loops.
