# domain/composite residual closeout (trivial pack #8238–#8253)

- Branch: `main`
- Fixed: **7**
- Rejected (partial): **1**
- Total: **8**

## Dispositions

- **#8238** `fixed` — DependencyResult.skipped leaves error_message=None (reason is non-error diagnostic only).
- **#8239** `fixed` (code) / reject ADR ceremony — AggregationFunction and EnricherCardinality are StrEnum; values unchanged; ADR-026 already owns composite config contract (no separate version-bump pack for trivial enum subclass).
- **#8241** `fixed` — FieldGroupDefinition rejects empty display_name.
- **#8242** `fixed` — EnricherFieldPairing normalizes fields list→tuple before validation.
- **#8248** `fixed` — ColumnGroupConfig compiles pattern with re at construction.
- **#8249** `fixed` — FieldGroupRegistry precomputes FieldGroupId rank map in __init__.
- **#8251** `fixed` — MergeConfig/AggregationConfig convert tuple-of-dicts same as list-of-dicts.
- **#8253** `fixed` — CompositePipelineState.allowed_transitions uses cached _STATE_TRANSITION_SETS.

## Validation
- `pytest tests/unit/domain/composite` green
- Residual tests: tests/unit/domain/composite/test_domain_composite_cr_residuals_8238_8253.py
- No tech-debt budget growth
