# 7775 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/batch_executor_dq_mixin.py`: In @src/bioetl/application/core/batch_executor_dq_mixin.py around lines 109 - 113, Initialize _dq_total_seen and _dq_reservoir_ranks in BatchExecutor.__init__ alongside the other DQ collection fields, then remove the per-record hasattr guards from the mixin. Remove _dq_total_s...
- **major** `src/bioetl/application/core/batch_executor_dq_mixin.py`: In @src/bioetl/application/core/batch_executor_dq_mixin.py around lines 103 - 131, Refactor `_reservoir_add` to maintain a per-stage max-heap of `(rank, sequence, item)` entries keyed by a stable stage name, replacing `_dq_reservoir_ranks` and `id(reservoir)` positional tracki...

            
