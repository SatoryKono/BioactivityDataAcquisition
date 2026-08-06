# 7837 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_transformer_finalization.py`: In @src/bioetl/application/core/batch_transformer_finalization.py around lines 138 - 157, Remove the run-scoped error_count fallback from _resolve_error_count so threshold evaluation uses only batch-local signals: batch_metrics.batch_error_count or state.quarantined_count. Pre...


