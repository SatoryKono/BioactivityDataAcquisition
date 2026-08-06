# 7771 [open]

## Findings (top)

            - **major** `src/bioetl/application/core/_batch_writer_gold_support.py`: In @src/bioetl/application/core/_batch_writer_gold_support.py at line 10, Remove the Mock import and replace the isinstance(validator, Mock) branch in the batch-writer logic with a capability check for the validator’s rebind_schema method. Update the validator protocol/type co...
- **major** `src/bioetl/application/core/_batch_writer_gold_support.py`: In @src/bioetl/application/core/_batch_writer_gold_support.py around lines 65 - 93, Update rebind_gold_validator_schema so schema rebinding is performed through a validator-owned clone/rebind API rather than reflection or private _strict/_dq_config attributes. Do not silently ...

            
