# RF-07A ProviderRegistry Call-Site Ledger

**Date:** 2026-03-20  
**Status:** Baseline collected and first migration slice applied

## Scope

Tracked call sites for:

- `ProviderRegistry.ensure_loaded`
- `ProviderRegistry.is_registered`
- `ProviderRegistry.create_adapter`
- `ProviderRegistry.build_data_source_creator`
- `ProviderRegistry.get_http_config`
- `create_provider_registry`

## Classification

| File | API usage | Category | Disposition |
|---|---|---|---|
| [`src/bioetl/composition/_pipeline_execution.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/_pipeline_execution.py) | `ProviderRegistry.ensure_loaded()` | production path | defer |
| [`src/bioetl/composition/bootstrap/runtime/pipeline.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/bootstrap/runtime/pipeline.py) | `ProviderRegistry.ensure_loaded()` | production path | defer |
| [`src/bioetl/composition/factories/pipeline/runner.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/runner.py) | `ProviderRegistry.ensure_loaded()` | production path | defer |
| [`src/bioetl/composition/runtime_builders/runner_builder.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/runtime_builders/runner_builder.py) | default `ensure_providers_loaded_fn=ProviderRegistry.ensure_loaded` | production path | defer |
| [`src/bioetl/composition/factories/datasource/http_client.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/datasource/http_client.py) | explicit `provider_registry` path for config lookup and validation | production path | migrated |
| [`src/bioetl/composition/factories/datasource/data_source_factory.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/datasource/data_source_factory.py) | `provider_registry` injection path | production path | retained and expanded |
| [`src/bioetl/composition/factories/pipeline/assembler.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/assembler.py) | explicit `provider_registry` threaded into creator resolution | production path | migrated |
| [`src/bioetl/composition/factories/pipeline/contract_validator.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/contract_validator.py) | explicit `provider_registry` threaded into `get_data_source_creator(...)` | production path | migrated |
| [`src/bioetl/composition/providers/registration.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/providers/registration.py) | `register_all_providers(registry=...)` | production path | retain |
| [`tests/unit/composition/providers/test_provider_registry.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/providers/test_provider_registry.py) | broad class-level registry API | test convenience | retain |
| [`tests/unit/composition/providers/test_registration.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/providers/test_registration.py) | `create_provider_registry()` | test convenience | retain |
| [`tests/unit/composition/factories/datasource/test_data_source_registry.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/factories/datasource/test_data_source_registry.py) | `create_provider_registry()` | test convenience | retain |
| [`tests/unit/composition/factories/datasource/test_data_sources.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/factories/datasource/test_data_sources.py) | `create_provider_registry()` | test convenience | retain |
| [`tests/unit/composition/factories/pipeline/test_runner_factory.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/factories/pipeline/test_runner_factory.py) | patches `ProviderRegistry.ensure_loaded` | compatibility path | retain for now |
| [`tests/unit/composition/runtime_builders/test_runner_builder.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/runtime_builders/test_runner_builder.py) | patches `ProviderRegistry.ensure_loaded` | compatibility path | retain for now |
| [`tests/unit/composition/bootstrap/test_bootstrap_entrypoints.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/bootstrap/test_bootstrap_entrypoints.py) | patches `ProviderRegistry.ensure_loaded` | compatibility path | retain for now |
| [`tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py) | asserts `ensure_loaded` bootstrap behavior | compatibility path | retain for now |

## Decision Support

### Migration-ready zone

The most migration-ready area is the datasource chain:

- [`data_source_factory.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/datasource/data_source_factory.py)
- [`http_client.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/datasource/http_client.py)

Reason:

- explicit registry injection already exists in `data_source_factory.py`;
- `http_client.py` was the first place where hidden default-registry access was reduced successfully;
- bootstrap/runtime can remain unchanged in the first wave.

The migration-safe boundary now extends one step further into the pipeline factory seam:

- [`assembler.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/assembler.py)
- [`contract_validator.py`](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/contract_validator.py)

### Deferred zone

Bootstrap and runner assembly remain explicitly deferred:

- they still use class-level `ensure_loaded()` as a shared convenience seam;
- tests are heavily normalized around that behavior;
- migrating them first would create a larger blast radius than the datasource chain.
