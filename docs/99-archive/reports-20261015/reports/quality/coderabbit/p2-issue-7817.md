# 7817 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_processing_runtime.py`: In @src/bioetl/application/core/batch_processing_runtime.py around lines 31 - 45, Replace the untyped data_source/getattr access in get_source_metadata with an explicit injected source-metadata port or an optional get_source_metadata capability on the data-source protocol. Upd...


