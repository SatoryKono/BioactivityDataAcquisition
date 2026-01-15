## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-24 - [Pandera Schema Conversion Overhead]
**Learning:** `PanderaModel.to_schema()` is not free. Calling it inside a hot loop (e.g., every batch write) introduces measurable overhead (~0.2ms per call). While small individually, it adds up over thousands of batches.
**Action:** Pre-calculate/cache schema artifacts (like column lists) in `__init__` or outside the processing loop. Avoid repeated calls to `to_schema()` or `columns` property if the schema is static.

## 2026-05-24 - [Schema Filtering Loop Trade-offs]
**Learning:** Iterating over `record.items()` to filter keys might be faster (~20%) than iterating over `schema_columns` when N (record size) ~ M (schema size), but it loses the implicit ordering provided by the schema column list.
**Action:** When order matters (e.g., for downstream CSV writers or deterministic output), stick to iterating over `schema_columns` even if slightly slower. Correctness and stability > micro-optimization.
