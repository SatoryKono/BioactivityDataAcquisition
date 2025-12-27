# Bolt's Performance Journal

## 2025-01-27 - [Pydantic Validation in Hot Paths]
**Learning:** Pydantic validation is significantly slower than standard Python class instantiation. In tight loops (processing millions of records), instantiating Pydantic models for every record just to access fields or serialize them is a massive bottleneck.
**Action:** For high-throughput ETL hot paths, prefer TypedDicts or raw dictionaries for intermediate data moving between layers (Bronze -> Silver), and only use Pydantic for the final strict domain boundary or config loading. If domain entities are needed, use `construct()` if data is already trusted, or optimized `__post_init__` in standard classes (frozen dataclasses) as done in `src/bioetl/domain/entities.py`.

## 2025-02-15 - [JSON Serialization Overhead]
**Learning:** Standard `json.dumps` is slow. `orjson` is much faster but requires careful handling of options (like `OPT_SORT_KEYS` for determinism).
**Action:** Use `orjson` in all `BatchWriter` implementations. Pre-calculate invariant metadata strings outside the loop to avoid repeated serialization/concatenation.
