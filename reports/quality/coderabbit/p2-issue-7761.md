# 7761 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/_batch_write_support.py`: In @src/bioetl/application/core/_batch_write_support.py at line 154, Remove the direct private-attribute access from all three call sites in the batch-write helpers. Expose a public tracking method on BatchWriter, such as track_batch_written, and invoke it from safe_write_laye...
- **major** `src/bioetl/application/core/_batch_write_support.py`: In @src/bioetl/application/core/_batch_write_support.py around lines 28 - 35, Update emit_domain_event to match its “Best-effort publish” contract by catching emitter failures and logging them through the existing LoggerPort available to _quarantine_schema_violation, while all...

            
