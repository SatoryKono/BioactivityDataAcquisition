# RF-04A Composition Seam Map

**Date:** 2026-03-20
**Status:** Completed analysis, decisions executed for RF-04B/RF-04C
**Parent plan:** [`rf-04-composition-hotspots-execution-plan-2026-03-20.md`](rf-04-composition-hotspots-execution-plan-2026-03-20.md)

## Purpose

This memo records the delegation map and seam decisions for the three RF-04 hotspot candidates:

- [`registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py)
- [`pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py)
- [`composite_support_service_builders.py`](../../src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py)

The goal is to decide `refactor now`, `closeout only`, or `defer` from actual assembly seams rather than raw file size.

## Summary Decisions

| File | Decision | Why |
| --- | --- | --- |
| [`registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py) | `closeout only` | one important seam is already extracted; remaining work is tightening profile assembly, not major decomposition |
| [`pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py) | `refactor now` | multiple entry points still mix distinct assembly responsibilities and already delegate into adjacent helper modules |
| [`composite_support_service_builders.py`](../../src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py) | `defer` | three existing builders are already cohesive and backed by targeted unit tests; evidence for a cleaner new seam is weak |

## 1. `registration_biblio.py`

### Delegation map

Current composition responsibilities are split across:

- adapter helper ownership in [`_registration_biblio_adapters.py`](../../src/bioetl/composition/providers/_registration_biblio_adapters.py)
- config normalization and HTTP data-source wrapping in [`_config_helpers.py`](../../src/bioetl/composition/providers/_config_helpers.py)
- contract/support ownership in [`_registration_contracts.py`](../../src/bioetl/composition/providers/_registration_contracts.py)
- provider-level wiring in [`registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py)

### Real seams found

There are two meaningful responsibilities left:

1. provider-specific request profile resolution
   - email/mailto/api-key lookup
   - provider-specific batch defaults
   - rate-limit override semantics

2. provider registry entry assembly
   - `ProviderConfig(...)`
   - `HttpConfig(...)`
   - `data_source_creator=partial(...)`

### Change coupling

The remaining coupling is mostly local to bibliographic provider setup:

- PubMed and OpenAlex share “credential or default email from settings” behavior.
- CrossRef and OpenAlex both carry mailto-style polite-pool configuration.
- `ProviderConfig` creation for all biblio providers still lives in one switch-like return mapping.

That is real composition logic, but it is no longer an uncontrolled hotspot. The file already delegates important adapter-creation concerns.

### Test net

- [`test_registration_data_sources.py`](../../tests/unit/composition/providers/test_registration_data_sources.py)
- [`test_registration_biblio_provider_configs.py`](../../tests/unit/composition/providers/test_registration_biblio_provider_configs.py)
- [`test_registration.py`](../../tests/unit/composition/providers/test_registration.py)
- architecture freeze and registry decomposition checks

### Decision

`closeout only`

### Why

This file no longer justifies being the main RF-04 decomposition wave. The correct next step is a small cleanup that makes provider-profile assembly easier to read, without introducing another layer of helper indirection unless it clearly reduces duplicated branch logic.

## 2. `pipeline_builder.py`

### Delegation map

The module already delegates into:

- [`runtime_managers.py`](../../src/bioetl/composition/factories/services/runtime_managers.py)
- [`pipeline_processing.py`](../../src/bioetl/composition/factories/services/pipeline_processing.py)

But the facade still owns several distinct responsibilities:

- `create_batch_processing_components(...)`
- `create_checkpoint_manager(...)`
- `create_record_processor_from_pipeline(...)`
- `_build_record_processor_config(...)`
- `create_batch_executor_from_pipeline(...)`

### Real seams found

The current file mixes at least four actual reasons to change:

1. component-stack assembly
   - `BatchMetricsRecorderService`
   - `QuarantineManagerService`
   - `BatchTransformer`
   - `BatchWriter`
   - `ColumnOrderer`

2. record-processor projection
   - pulling pipeline config into builder arguments
   - callback projection
   - schema/table/write-mode mapping

3. processor-config and validator construction
   - `RecordProcessorConfig`
   - `PanderaGoldValidator`

4. executor orchestration wiring
   - runtime managers
   - processing service
   - extraction loop
   - state service
   - FSM/dependencies bundle

### Change coupling

This module is likely to change when any of the following move:

- batch processing stack contracts,
- record processor input shape,
- validator / config assembly semantics,
- executor dependency wiring.

That is a strong indicator of mixed reasons to change. It is also important that the file already had earlier extractions to helper modules; this usually means the remaining responsibilities are still broad enough to justify a second seam pass.

### Test net

- [`test_pipeline_builder_unit.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_unit.py)
- [`test_pipeline_builder_batch_executor.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py)
- [`test_services_factory.py`](../../tests/unit/composition/factories/services/test_services_factory.py)
- [`test_builder_unit.py`](../../tests/unit/composition/factories/services/test_builder_unit.py)
- [`test_smoke_composition.py`](../../tests/smoke/test_smoke_composition.py)

### Decision

`refactor now`

### Why

This is the strongest RF-04 hotspot because:

- the file still mixes several stable concerns,
- the seams are legible,
- adjacent helpers already exist,
- the protective test net is strong enough for a medium-risk structural wave.

### Recommended target shape

- keep [`pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py) as the public facade,
- extract 2-3 themed helpers,
- avoid generic utility modules,
- preserve caller-facing contracts during the first decomposition wave.

## 3. `composite_support_service_builders.py`

### Delegation map

The module already has three explicit public builders:

- `build_execution_support_services(...)`
- `build_runtime_management_services(...)`
- `build_merge_dependencies(...)`

These are backed by three bundle dataclasses:

- `ExecutionSupportServicesBundle`
- `RuntimeManagementServicesBundle`
- `MergeDependenciesBundle`

### Real seams found

Unlike `pipeline_builder.py`, this module already appears to be separated by runtime phase:

1. execution support
2. runtime management
3. merge dependency assembly

That is already a seam-first design.

### Change coupling

There is still some structural weight in `build_merge_dependencies(...)`, but the weight is currently cohesive:

- deduplicator / aggregator / renamer / orderers
- coalesce and conflict services
- join key resolution
- join executor
- dependency joiner
- join planner

This is a large collaborator bundle, but it is all in one merge-assembly reason to change. The file does not yet show the same “mixed responsibilities in one facade” problem as `pipeline_builder.py`.

### Test net

There is targeted unit coverage here after all:

- [`test_composite_support_service_builders.py`](../../tests/unit/composition/bootstrap/runtime/test_composite_support_service_builders.py)
- plus architecture boundary coverage in [`test_composite_cli_runtime_config_boundaries.py`](../../tests/architecture/test_composite_cli_runtime_config_boundaries.py)

### Decision

`defer`

### Why

This is not “unsafe to touch”.
It is “not yet justified to touch”.

The current code already has explicit bundle boundaries and targeted tests. Without stronger evidence of duplicated wiring elsewhere or multiple independent change axes inside one builder, decomposing it now would be churn-heavy and likely worsen discoverability.

## Outcome

The recommended next step from this memo has now been executed:

1. RF-04B completed as a low-risk `registration_biblio` closeout slice.
2. RF-04C completed as the main `pipeline_builder` decomposition wave.
3. [`composite_support_service_builders.py`](../../src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py) remains intentionally outside implementation scope until stronger evidence appears.
