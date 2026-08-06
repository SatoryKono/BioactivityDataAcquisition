# 7781 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_writer_io_mixin.py`: In @src/bioetl/application/core/batch_writer_io_mixin.py at line 1, Replace the module-wide attr-defined suppression and Any-based collaborator defaults in the batch writer mixin with an explicit typed host surface, preferably a Protocol implemented through constructor-injecte...
- **major** `src/bioetl/application/core/batch_writer_io_mixin.py`: In @src/bioetl/application/core/batch_writer_io_mixin.py around lines 186 - 227, Align the non-deferred Gold path in the batch-writing method around prepare_gold_records, validate_gold_records, and _apply_renames_to_records so schema_payload, records, and column_order use the ...

            
