# 7813 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_executor_loop_progress.py`: In @src/bioetl/application/core/batch_executor_loop_progress.py around lines 107 - 123, Add unit tests for ensure_extraction_not_shutdown covering both paths: when shutdown_requested is true, verify save_checkpoint_now receives the exact records_fetched and resume_offset value...


