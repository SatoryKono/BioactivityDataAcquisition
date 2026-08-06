# 7816 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_metrics.py`: In @src/bioetl/application/core/batch_metrics.py around lines 228 - 242, The Silver rejection path in the surrounding metrics method currently exits when _metrics is unset, preventing PipelineMetricsRecorder and _record_silver_removal_accounting from running. Remove the `if no...


