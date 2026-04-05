# Provider Registry Runtime Ownership

## Research Question

After RF-07D1/D2/D3, do runtime/bootstrap paths still need explicit
`ProviderRegistry` instance ownership, or is the named runtime bootstrap seam
already sufficient for the current architecture?

## Scope

- runtime/bootstrap provider bootstrap flow in:
  - `src/bioetl/composition/_pipeline_execution.py`
  - `src/bioetl/composition/bootstrap/runtime/pipeline.py`
  - `src/bioetl/composition/factories/pipeline/runner.py`
  - `src/bioetl/composition/runtime_builders/runner_builder.py`
- adjacent explicit-registry production paths in:
  - `src/bioetl/composition/factories/datasource/`
  - `src/bioetl/composition/factories/pipeline/`
- architecture guards and unit tests that constrain future changes
- active RF-07 plan artifacts that define intended migration boundaries

## Out Of Scope

- removing the default provider registry compatibility layer
- repo-wide bans on class-level registry access
- speculative redesigns that are not yet supported by runtime evidence

## Evaluation Focus

1. Is runtime bootstrap already explicit and testable enough through the named seam?
1. Do runtime callers naturally own a `ProviderRegistry` instance today?
1. Where does explicit registry instance threading already produce clear value?
1. What evidence would justify a later RF-07D4 wave instead of stopping here?
