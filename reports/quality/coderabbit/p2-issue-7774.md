# 7774 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_executor_dq_helpers.py`: In @src/bioetl/application/core/batch_executor_dq_helpers.py around lines 190 - 195, Update build_dq_report_context to remove the hidden current_utc_time() fallback and require the typed PipelineContext’s started_at, failing explicitly when it is absent; access started_at and ...
- **major** `src/bioetl/application/core/batch_executor_dq_helpers.py`: In @src/bioetl/application/core/batch_executor_dq_helpers.py around lines 141 - 153, Update extract_dq_entity so it removes the schema qualifier from silver_table before removing the layer prefix, preserving underscores within the entity name; ensure qualified names such as si...

            
