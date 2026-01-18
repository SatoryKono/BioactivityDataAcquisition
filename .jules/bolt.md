## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-24 - [Re-applying In-Place Dictionary Filtering]
**Learning:** Found that `BatchWriter.write_gold` was using a dictionary comprehension to filter keys, contrary to existing memory stating it used in-place modification. The comprehension `[{k: r[k] for k in schema_columns if k in r} for r in records]` is clean but slow (Allocating N dicts).
**Action:** Re-implemented in-place filtering: `to_remove = [k for k in r if k not in schema_columns]; for k in to_remove: del r[k]`. Benchmarked 7.6x speedup. Always verify that "known" optimizations are actually present in the code.
