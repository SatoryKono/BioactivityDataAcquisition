# 7818 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_processing_service.py`: In @src/bioetl/application/core/batch_processing_service.py around lines 154 - 157, Replace the private `_debug_export_service` lookup in `debug_export_service` with an explicit typed collaborator port on `BatchProcessingSupportService`, or inject that collaborator through `Ba...


