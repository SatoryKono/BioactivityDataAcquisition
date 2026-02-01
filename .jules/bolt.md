## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [Schema-Driven Filtering]
**Learning:** When filtering large dictionaries (records) against a known schema, iterating over the schema keys is faster than iterating over the record keys if the record has many extra fields (common in Silver layer ETL). This avoids checking irrelevant fields.
**Action:** Use `for key in schema.names: if key in record:` pattern instead of `key for key in record if key in schema` when `len(record) > len(schema)`.
