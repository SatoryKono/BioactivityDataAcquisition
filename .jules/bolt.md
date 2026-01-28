## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [Schema-Driven vs Record-Driven Iteration]
**Learning:** In ETL pipelines (specifically Silver layer), raw records often contain many fields that are excluded from the target schema. Iterating over `schema.names` ($N \approx 50$) instead of `record.keys()` ($N \approx 1000$) reduces loop overhead significantly when filtering fields.
**Action:** When filtering dictionaries against a fixed schema, verify the cardinality of both sides. If schema is small and fixed, and inputs are large and dirty, invert the loop to iterate over the schema. This yielded a 2.1x speedup in `SilverWriter`.
