# 7796 [open]

## Findings (top)

- **major** `src/bioetl/application/core/_batch_processing_layer_write_support.py`: In @src/bioetl/application/core/_batch_processing_layer_write_support.py at line 35, Replace the broad Callable annotation for execute_with_span with a Protocol defining the span runner’s concrete __call__ signature, matching the arguments and return type used by safe_write_la...


