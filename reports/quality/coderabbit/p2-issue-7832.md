# 7832 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_runtime_failure_policy.py`: In @src/bioetl/application/core/batch_runtime_failure_policy.py around lines 13 - 17, Remove KeyError and AttributeError from PIPELINE_EXECUTION_ERRORS, leaving only the established domain and I/O exception types such as OPERATION_ERRORS. Ensure batch_executor_state_flow.py no...


