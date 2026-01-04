## 2026-05-24 - Caching Schema Columns
**Learning:** In `BatchWriter`, iterating over Pandera schema columns repeatedly per batch caused unnecessary overhead.
**Action:** Move schema column extraction to `__init__` for batch processors. Always check if schema definitions are static and cacheable.
