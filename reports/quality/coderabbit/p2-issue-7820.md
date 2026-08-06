# 7820 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_progress_service.py`: In @src/bioetl/application/core/batch_progress_service.py around lines 16 - 43, Replace the object-typed data_source and reflective getattr/cast logic in BatchProgressService with an explicit narrow Protocol port exposing async get_total_records, and inject that typed capabili...


