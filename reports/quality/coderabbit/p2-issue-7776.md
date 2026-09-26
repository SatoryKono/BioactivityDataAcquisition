# 7776 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_executor_helpers.py`: In @src/bioetl/application/core/batch_executor_helpers.py around lines 92 - 127, Replace the private Protocol members used by apply_batch_execution_state_update and apply_processed_batch_outcome with explicit public operations: append the source batch ID through append_source_...
- **major** `src/bioetl/application/core/batch_executor_helpers.py`: In @src/bioetl/application/core/batch_executor_helpers.py around lines 44 - 53, Update the batch contracts and executor DQ buffers to preserve concrete result types: use list[SilverRecord] for TransformerExecutionOwner outputs and the related TransformResult, BatchProcessingOu...

            
