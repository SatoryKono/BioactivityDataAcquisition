## 2026-05-24 - [Dictionary Copy Overhead in Hot Loops]
**Learning:** `dict.copy()` in Python is relatively fast but adds up significantly in tight loops (e.g., 50k+ iterations). When creating "enriched" records for storage (like adding `_source_batch_id`), copying every record just to add one field is wasteful if the source list is transient.
**Action:** Verify if the list of records is used elsewhere. If not (and it's passed by value/reference solely for this operation), modify the dictionaries in-place. This reduces memory pressure and execution time (~35% speedup observed).

## 2026-05-25 - [Static Dictionary Lookup Optimization]
**Learning:** Re-defining a constant dictionary inside a method that is called repeatedly (e.g., `_parse_month` in a transformer) creates unnecessary overhead. Moving it to a class constant (`ClassVar`) avoids this recreation cost.
**Action:** Move static lookup dictionaries to class-level constants. Observed a ~4x speedup in the `_parse_month` method benchmark.

## 2026-05-26 - [String Normalization in Hot Loops]
**Learning:** Calling `.lower()` on constant patterns or search terms inside a tight loop (e.g., PTM extraction for features) can add significant overhead (~7%). This is especially true when processing large arrays of features per record.
**Action:** Pre-normalize constant patterns outside the loop. Use the walrus operator `:=` to avoid redundant dictionary lookups in transformer/extractor methods.
