# 7815 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_memory_manager.py`: In @src/bioetl/application/core/batch_memory_manager.py around lines 172 - 176, Update the recovery-size calculation in the batch recovery logic so every current_size below _initial_batch_size produces measurable growth despite integer conversion, while still capping at _initi...


