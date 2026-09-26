# 7834 [open]

## Findings (top)

- **major** `src/bioetl/application/core/batch_transformer_attempt_success.py`: In @src/bioetl/application/core/batch_transformer_attempt_success.py around lines 79 - 91, Replace the reflective `_resolve_gold_filter_details` lookup with an explicit filter-details port or callback result carrying the already computed `FilterDecision`. Update `build_transfo...


