# File-Size Decomposition Migration Notes (2026-03-06)

## Scope
P1 decomposition for top file-size offenders with backward-compatible facades.

## Public API Compatibility
The following import paths remain valid (facade preserved):

- `bioetl.application.composite.checkpoint`
- `bioetl.application.core.base_transformer`
- `bioetl.domain.exceptions.infrastructure`
- `bioetl.domain.ports.noop`
- `bioetl.domain.ports.observability`

No call-site migration is required for existing `from ... import ...` usage.

## Internal Module Split

### `application/composite/checkpoint.py` -> `application/composite/checkpoint/`
- `__init__.py` (facade)
- `state.py` (`CompositeCheckpointState`)
- `service.py` (`CompositeCheckpointService`, `CompositeCheckpointManager` alias)

### `application/core/base_transformer.py` -> `application/core/base_transformer/`
- `__init__.py` (facade)
- `base.py` (`BaseTransformer`)
- `types.py` (`ValueObjectWithFromRaw`, `T`, `V`)
- `errors.py` (`TransformationError`, `FilteredOutError`)
- `contract_policy.py` (`_DefaultContractPolicy`)

### `domain/exceptions/infrastructure.py` -> `domain/exceptions/infrastructure/`
- `__init__.py` (facade + helper re-exports used by tests)
- `_base.py` (`InfrastructureError`)
- `_storage.py` (storage/schema exceptions)
- `_delta.py` (delta-specific exceptions and helper formatters)

### `domain/ports/noop.py` -> `domain/ports/noop/`
- `__init__.py` (facade)
- `_tracing.py`
- `_metrics.py`
- `_audit_pii.py`
- `_memory_metadata.py`

### `domain/ports/observability.py` -> `domain/ports/observability/`
- `__init__.py` (facade)
- `tracing.py`
- `metrics.py`
- `logging.py`
- `dq_monitor.py`

## Notes
- File-size exemptions for all decomposed legacy module paths were removed.
- Additional near-threshold modules were reduced below default limits without behavior changes.
