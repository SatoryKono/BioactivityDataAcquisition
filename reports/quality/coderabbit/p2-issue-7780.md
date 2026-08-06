# 7780 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_writer_columns_mixin.py`: In @src/bioetl/application/core/batch_writer_columns_mixin.py at line 1, Remove the file-wide mypy attr-defined suppression and replace the Any annotations for _column_orderer and _data_schema with small Protocols under TYPE_CHECKING. Define the protocols for order_column_name...
- **major** `src/bioetl/application/core/batch_writer_columns_mixin.py`: In @src/bioetl/application/core/batch_writer_columns_mixin.py around lines 41 - 48, Update _project_via_to_schema, _project_via_select_columns, and _project_pyarrow_schema to return None from their exception handlers instead of the original schema, so _project_schema_for_layer...

            
