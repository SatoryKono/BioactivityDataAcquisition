______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-26'

______________________________________________________________________

# Composite Validation Service

## Purpose

`CompositeValidator` is the domain service entrypoint for composite
config validation before execution. It combines structural checks, deep preflight
checks, and governance decisioning into a single report. Construction of the
default service wiring now lives in
`bioetl.composition.factories.dq.create_composite_validation_service()`.

Source of truth:

- `src/bioetl/domain/behavior/composite_validation_layer.py`

## Public API

### `CompositeValidationConfig`

Configuration envelope with:

- `pipeline_name`
- `composite_config`
- `execution_context` (optional)
- `strict_mode`
- `governance_policy`

### `CompositeValidator.validate_composite(config)`

Returns `CompositeValidationReport` with:

- `structural_result`
- `deep_preflight_result`
- `runtime_guard_result` (currently `None` in this layer)
- `execution_decision` (from `PreflightGovernor`)

## Validation flow

1. Structural validation

- schema shape checks for required top-level fields:
  - `sources`
  - `merge_strategy`
  - `output_schema`

2. Deep preflight validation

- aggregation config validation via `AggregationValidator`
- cross-validation config validation via `CrossValidationValidator`
- field priorities and lineage config checks

3. Governance application

- apply configured governance policy to produced validation report
- return final `execution_decision`

## Dependencies

- `AggregationValidator`
- `CrossValidationValidator`
- `PreflightGovernor`
- helpers from `composite_validation_helpers.py`

These collaborators are injected into `CompositeValidator` by the
composition layer; the domain module no longer assembles them internally.

## Related docs

- [Composite Validation Layer](composite-validation-layer.md)
- [DQ Contract System](../contracts/dq-contracts.md)
- [Configuration Runtime Artifacts](config-runtime-artifacts.md)
- [Phased Migration Support](phased-migration.md)
