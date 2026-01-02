## 2026-05-24 - Schema Column Caching in BatchWriter
**Learning:** Repetitive schema introspection (e.g., `pandera.DataFrameModel.to_schema()`) in hot loops is a significant bottleneck. Moving this logic to initialization (O(1)) avoids repeated O(N) conversions per batch.
**Action:** Always hoist schema introspection/conversion out of processing loops into `__init__` or `__post_init__` for long-lived worker objects.
