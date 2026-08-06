# 7814 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_executor_runtime_state.py`: In @src/bioetl/application/core/batch_executor_runtime_state.py around lines 41 - 43, Remove the cast(None) sentinel from the _runtime_state declaration in BatchExecutorRuntimeState, leaving the annotated attribute without a class-level value so missing executor initialization...


