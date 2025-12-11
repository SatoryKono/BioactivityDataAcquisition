# Config Dependency Map

Generated: 2025-12-11

This document maps all dependencies for `src/bioetl/domain/configs/` to ensure safe refactoring.

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total files in configs/ | 16 |
| Classes in pipeline.py | 24 |
| External consumers (src/) | 32 files |
| Test files using configs/ | 28 files |
| Deprecated aliases | 4 |

---

## Module Structure

```
src/bioetl/domain/configs/
├── __init__.py          # Main exports (re-exports from all modules)
├── _compat.py           # Deprecated aliases with warnings
├── base.py              # Legacy compatibility layer (re-exports from pipeline.py)
├── contracts.py         # PipelineConfigLoaderProtocol
├── data_flow.py         # DataFlowConfig
├── defaults.py          # DefaultsConfig and related
├── execution.py         # ExecutionConfig
├── identity.py          # PipelineIdentityConfig
├── manifest.py          # PipelineManifest
├── normalization.py     # NormalizationConfig
├── pipeline.py          # Main config file (854 lines, 24 classes)
├── pipeline_parts.py    # Dataclass-based config parts
├── profile.py           # ProfileConfig
├── sink.py              # DataSinkConfig, OutputOptionsConfig
├── source.py            # DataSourceConfig, CsvInputConfig
└── transform.py         # TransformConfig
```

---

## Internal Dependencies (configs/ → configs/)

```yaml
internal_dependencies:
  pipeline.py:
    imports_from:
      - data_flow.py: [DataFlowConfig]
      - identity.py: [PipelineIdentityConfig]
      - normalization.py: [NormalizationConfig]
      - sink.py: [DataSinkConfig, OutputOptionsConfig]
      - source.py: [CsvInputConfig, DataSourceConfig]
      - transform.py: [TransformConfig]
    type_checking_imports:
      - execution.py: [ExecutionConfig]
      - manifest.py: [PipelineManifest]
    exported_to:
      - __init__.py  # re-exports 28 classes
      - base.py      # legacy compatibility layer
      - defaults.py  # uses HashingConfig, HttpClientConfig, NormalizationConfig
      - execution.py # uses PaginationConfig, PipelineStagesConfig, RuntimeConfig
      - manifest.py  # uses QualityConfig, ProviderConfigUnion
      - _compat.py   # TYPE_CHECKING only

  manifest.py:
    imports_from:
      - data_flow.py: [DataFlowConfig]
      - execution.py: [ExecutionConfig]
      - identity.py: [PipelineIdentityConfig]
      - pipeline.py: [ProviderConfigUnion, QualityConfig]
    type_checking_imports:
      - pipeline.py: [PipelineConfig]
    exported_to:
      - __init__.py
      - pipeline.py  # TYPE_CHECKING only

  execution.py:
    imports_from:
      - pipeline.py: [PaginationConfig, PipelineStagesConfig, RuntimeConfig]
      - transform.py: [TransformConfig]
    exported_to:
      - __init__.py
      - manifest.py
      - pipeline.py  # TYPE_CHECKING only

  defaults.py:
    imports_from:
      - pipeline.py: [HashingConfig, HttpClientConfig, NormalizationConfig]
    exported_to:
      - __init__.py

  data_flow.py:
    imports_from:
      - sink.py: [DataSinkConfig]
      - source.py: [DataSourceConfig]
    exported_to:
      - __init__.py
      - pipeline.py
      - manifest.py

  identity.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py
      - pipeline.py
      - manifest.py

  normalization.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py
      - pipeline.py
      - defaults.py

  sink.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py
      - pipeline.py
      - data_flow.py

  source.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py
      - pipeline.py
      - data_flow.py

  transform.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py
      - pipeline.py
      - execution.py

  profile.py:
    imports_from: []  # No internal imports
    exported_to:
      - __init__.py

  contracts.py:
    imports_from: []  # TYPE_CHECKING only
    type_checking_imports:
      - __init__.py: [PipelineConfig]  # via bioetl.domain.configs
    exported_to:
      - __init__.py

  pipeline_parts.py:
    imports_from: []  # No internal imports, uses dataclasses
    exported_to: []   # Not exported via __init__.py

  base.py:
    imports_from:
      - pipeline.py: [ALL classes - legacy compatibility]
    exported_to: []   # Legacy layer, not re-exported

  _compat.py:
    imports_from: []
    type_checking_imports:
      - pipeline.py: [HttpClientConfig, ProviderHttpConfig]
    exported_to:
      - __init__.py  # lazy loading
```

---

## Classes in pipeline.py

```yaml
pipeline_py_classes:
  # HTTP Configuration
  - HttpClientConfig:
      lines: 43-109
      dependencies: []
      used_by_internal: [ProviderHttpConfig, RuntimeConfig, defaults.py]

  - ProviderHttpConfig:
      lines: 111-117
      dependencies: [HttpClientConfig]
      used_by_internal: [BaseProviderConfig, _compat.py]

  # Storage & Observability
  - StorageConfig:
      lines: 119-127
      dependencies: []
      used_by_internal: [RuntimeConfig]

  - LoggingConfig:
      lines: 129-137
      dependencies: []
      used_by_internal: [ObservabilityConfig]

  - MetricsConfig:
      lines: 139-156
      dependencies: []
      used_by_internal: [ObservabilityConfig]

  # Quality Control
  - DeterminismConfig:
      lines: 158-167
      dependencies: []
      used_by_internal: [QualityConfig]

  - QualityControlConfig:
      lines: 169-180
      dependencies: []
      used_by_internal: [QualityConfig]

  # Hashing
  - CanonicalizationConfig:
      lines: 182-195
      dependencies: []
      used_by_internal: [HashingConfig]

  - BusinessKeyConfig:
      lines: 197-204
      dependencies: []
      used_by_internal: [HashingConfig]

  - HashingConfig:
      lines: 206-223
      dependencies: [CanonicalizationConfig, BusinessKeyConfig]
      used_by_internal: [QualityConfig, defaults.py]

  # Feature Flags
  - InterfaceFeaturesConfig:
      lines: 225-232
      dependencies: []
      used_by_internal: [FeatureFlagsConfig]

  # Pipeline Stages
  - PipelineStagesConfig:
      lines: 234-245
      dependencies: []
      used_by_internal: [PipelineConfig, execution.py]

  - PaginationConfig:
      lines: 33-41
      dependencies: []
      used_by_internal: [RuntimeConfig, execution.py]

  # Provider Configs
  - BaseProviderConfig:
      lines: 247-350
      dependencies: [ProviderHttpConfig]
      used_by_internal: [ChemblSourceConfig, DummyProviderConfig]

  - ChemblSourceConfig:
      lines: 352-378
      dependencies: [BaseProviderConfig]
      used_by_internal: [ProviderConfigUnion]

  - DummyProviderConfig:
      lines: 380-384
      dependencies: [BaseProviderConfig]
      used_by_internal: [ProviderConfigUnion]

  - ProviderConfigUnion:
      lines: 386-389
      type: TypeAlias
      dependencies: [ChemblSourceConfig, DummyProviderConfig]
      used_by_internal: [PipelineConfig, manifest.py]

  # Aggregate Configs
  - RuntimeConfig:
      lines: 392-412
      dependencies: [PaginationConfig, HttpClientConfig, StorageConfig, CsvInputConfig]
      used_by_internal: [PipelineConfig, execution.py]

  - ObservabilityConfig:
      lines: 414-421
      dependencies: [LoggingConfig, MetricsConfig]
      used_by_internal: [PipelineConfig]

  - QualityConfig:
      lines: 423-434
      dependencies: [DeterminismConfig, QualityControlConfig, HashingConfig, NormalizationConfig]
      used_by_internal: [PipelineConfig, manifest.py]

  - FeatureFlagsConfig:
      lines: 436-480
      dependencies: [InterfaceFeaturesConfig]
      used_by_internal: [PipelineConfig]

  # Main Pipeline Config
  - PipelineConfig:
      lines: 482-808
      dependencies:
        - PipelineIdentityConfig
        - DataFlowConfig
        - PipelineStagesConfig
        - RuntimeConfig
        - ObservabilityConfig
        - QualityConfig
        - FeatureFlagsConfig
        - TransformConfig
        - ProviderConfigUnion
      used_by_internal: [manifest.py, contracts.py]

  # Deprecated Aliases
  - ClientConfig:
      lines: 852
      type: alias
      target: HttpClientConfig

  - HttpClientSettings:
      lines: 853
      type: alias
      target: HttpClientConfig
```

---

## External Dependencies (→ configs/)

```yaml
external_dependencies:
  # Application Layer
  PipelineConfig:
    application/:
      - application/bootstrap.py: [PipelineConfigLoaderProtocol]
      - application/container.py: [PipelineConfig]
      - application/contracts.py: [PipelineConfig]
      - application/orchestrator.py: [PipelineConfig]
      - application/config/runtime.py: [PipelineConfig, PipelineConfigLoaderProtocol]
      - application/factories/hooks.py: [PipelineConfig]
      - application/factories/record_source.py: [PipelineConfig]
      - application/factories/runtime_factory.py: [PipelineConfig]
      - application/factories/service_factory.py: [PipelineConfig]
      - application/factories/services.py: [PipelineConfig]
      - application/factories/transform_factory.py: [PipelineConfig]
      - application/helpers/primary_key.py: [PipelineConfig]
      - application/pipelines/base.py: [PipelineConfig]
      - application/pipelines/chembl/base.py: [ChemblSourceConfig, PipelineConfig]
      - application/services/background_executor.py: [PipelineConfig]
      - application/services/config_migration_service.py: [PipelineConfig]
      - application/services/configuration_service.py: [PipelineConfig]
      - application/use_cases/run_pipeline.py: [PipelineConfig, PipelineConfigLoaderProtocol]
      - application/files/csv_record_source.py: [ChemblSourceConfig, CsvInputConfig]

  # Domain Layer
  domain/:
    - domain/providers.py: [BaseProviderConfig, HttpClientConfig]
    - domain/transform/contracts.py: [NormalizationConfig]
    - domain/ports/config_loader_port.py: [PipelineConfig]
    - domain/ports/output.py: [QualityControlConfig]

  # Infrastructure Layer
  infrastructure/:
    - infrastructure/config/loader.py: [PipelineConfig]
    - infrastructure/config/defaults_loader.py: [DefaultsConfig, HashingDefaultsConfig, NetworkDefaultsConfig, NormalizationDefaultsConfig, SourceDefaultsConfig]
    - infrastructure/config/provider_registry.py: [ProviderHttpConfig]
    - infrastructure/config/models.py: [DEPRECATED - re-exports from domain.configs]
    - infrastructure/adapters/config_loader_adapter.py: [PipelineConfig]
    - infrastructure/output/unified_loader_impl.py: [DeterminismConfig, QualityControlConfig]
    - infrastructure/output/factories.py: [DeterminismConfig, QualityControlConfig]
    - infrastructure/output/components/metadata_builder.py: [QualityControlConfig]
    - infrastructure/clients/base/impl/_http_transport.py: [HttpClientConfig]
    - infrastructure/clients/base/factories.py: [HttpClientConfig]
    - infrastructure/clients/chembl/factories.py: [ChemblSourceConfig, HttpClientConfig]
    - infrastructure/clients/chembl/provider.py: [ChemblSourceConfig, HttpClientConfig]
    - infrastructure/chembl_client.py: [ChemblSourceConfig]

  # Interfaces Layer
  interfaces/:
    - interfaces/application_context.py: [PipelineConfigLoaderProtocol]
    - interfaces/bootstrap_factory.py: [PipelineConfig, PipelineConfigLoaderProtocol]
    - interfaces/composition_root.py: [HttpClientConfig, PipelineConfig, PipelineConfigLoaderProtocol]
    - interfaces/factories/infrastructure.py: [HttpClientConfig, PipelineConfigLoaderProtocol]

  # Tools
  tools/:
    - tools/debug_assay_fetch.py: [ChemblSourceConfig]
    - tools/debug_assay_fetch_v2.py: [ChemblSourceConfig]
```

---

## Test Coverage

```yaml
test_coverage:
  # Direct config tests
  domain_config_tests:
    - tests/bioetl/domain/test_pipeline_config.py: [PipelineConfig]
    - tests/bioetl/domain/test_data_flow_config.py: [DataFlowConfig, DataSinkConfig, DataSourceConfig]
    - tests/bioetl/domain/test_interface_features_config.py: [InterfaceFeaturesConfig]
    - tests/bioetl/domain/test_config_loader.py: [ChemblSourceConfig]
    - tests/bioetl/domain/test_config_migration.py: [config migration tests]

  # Integration tests
  integration_tests:
    - tests/integration/test_config_loading.py
    - tests/integration/test_provider_registry_loader.py: [DummyProviderConfig]
    - tests/integration/test_unified_writer_integration.py: [DeterminismConfig, QualityControlConfig]
    - tests/integration/application/test_container_integration.py: [multiple configs]

  # Application tests using configs
  application_tests:
    - tests/bioetl/application/test_container.py: [multiple configs]
    - tests/bioetl/application/test_container_factories.py: [PipelineConfig]
    - tests/bioetl/application/test_bootstrap.py: [PipelineConfigLoaderProtocol]
    - tests/bioetl/application/test_container_schema_bootstrap.py: [multiple configs]
    - tests/bioetl/application/test_pipeline_container_contract.py: [ClientConfig, DummyProviderConfig, PipelineConfig]
    - tests/bioetl/application/test_provider_loader_port.py: [ClientConfig, DummyProviderConfig, PipelineConfig]
    - tests/bioetl/application/helpers/test_primary_key.py: [multiple configs]
    - tests/bioetl/application/pipelines/chembl/test_config_resolution.py: [ChemblSourceConfig, ProviderHttpConfig]
    - tests/bioetl/application/pipelines/chembl/test_pk_resolution.py: [ChemblSourceConfig, ProviderHttpConfig]
    - tests/bioetl/application/files/test_app_csv_record_source.py: [CsvInputConfig]

  # Infrastructure tests
  infrastructure_tests:
    - tests/bioetl/infrastructure/config/test_provider_registry.py: [multiple configs]
    - tests/bioetl/infrastructure/clients/chembl/test_factories.py: [ChemblSourceConfig, HttpClientConfig]
    - tests/bioetl/infrastructure/clients/chembl/test_provider.py: [ChemblSourceConfig, ClientConfig]
    - tests/bioetl/infrastructure/clients/base/test_http_transport.py: [ClientConfig]
    - tests/bioetl/infrastructure/output/components/test_metadata_builder.py: [QualityControlConfig]
    - tests/bioetl/infrastructure/files/test_csv_record_source.py: [CsvInputConfig]
    - tests/bioetl/infrastructure/test_deprecation_warnings.py: [PipelineConfig]

  # Pipeline tests
  pipeline_tests:
    - tests/bioetl/pipelines/chembl/test_extract_pipeline_errors.py: [multiple configs]
    - tests/bioetl/pipelines/chembl/activity/test_extract.py: [ChemblSourceConfig, CsvInputConfig, ProviderHttpConfig]

  # CLI tests
  cli_tests:
    - tests/bioetl/interfaces/cli/test_cli.py: [multiple configs including ProviderHttpConfig]

  # Project rules tests
  project_rules_tests:
    - tests/project_rules/test_config_validation.py: [PipelineConfig]
    - tests/project_rules/test_project_rules.py: [HashingConfig, NormalizationConfig]

  # Fixtures
  fixtures:
    - tests/conftest.py:
        imports:
          - PipelineConfig
          - DataFlowConfig
          - PipelineIdentityConfig
          - ChemblSourceConfig
          - ProviderHttpConfig
          - DataSinkConfig
          - DataSourceConfig
        provides:
          - mock_config: PipelineConfig fixture
```

---

## Orphaned/Low-Usage Classes

Classes with zero or minimal external usage (candidates for review):

```yaml
orphaned_classes:
  # Potentially unused externally
  - pipeline_parts.py:
      classes:
        - HashingConfiguration  # dataclass, not used externally
        - IndexConfiguration    # dataclass, not used externally
        - MetadataConfiguration # dataclass, not used externally
        - ErrorHandlingConfiguration # dataclass, not used externally
        - PipelinePartsConfiguration # dataclass, not used externally
      status: "Not exported via __init__.py, consider removal or documentation"

  # Low external usage
  - ProfileConfig:
      file: profile.py
      external_usage: 0 direct imports found
      status: "Exported but no external consumers - verify if needed"

  # Deprecated aliases (scheduled for removal in v3.0)
  - _compat.py:
      aliases:
        - ClientConfig -> HttpClientConfig
        - HttpClientSettings -> ProviderHttpConfig
        - HttpClientDefaults -> HttpClientConfig
        - HTTP_CLIENT_DEFAULTS -> HttpClientConfig()
      status: "Deprecated, emit warnings, remove in v3.0"

  # Legacy layer
  - base.py:
      purpose: "Legacy compatibility layer"
      status: "Re-exports from pipeline.py, consider deprecation"
```

---

## Circular Dependency Analysis

```yaml
circular_dependencies:
  detected: false
  notes: |
    No circular dependencies detected between configs/ modules.

    The architecture uses TYPE_CHECKING imports to break potential cycles:
    - pipeline.py uses TYPE_CHECKING for execution.py and manifest.py
    - manifest.py uses TYPE_CHECKING for pipeline.py (PipelineConfig)
    - contracts.py uses TYPE_CHECKING for PipelineConfig

    Import order (safe):
    1. normalization.py, transform.py, sink.py, source.py (leaf modules)
    2. identity.py, profile.py, contracts.py, pipeline_parts.py (leaf modules)
    3. data_flow.py (imports sink, source)
    4. pipeline.py (imports data_flow, identity, normalization, sink, source, transform)
    5. defaults.py (imports pipeline)
    6. execution.py (imports pipeline, transform)
    7. manifest.py (imports data_flow, execution, identity, pipeline)
    8. _compat.py (TYPE_CHECKING only)
    9. base.py (imports pipeline - legacy)
    10. __init__.py (imports all)
```

---

## Refactoring Recommendations

### High Priority

1. **Split pipeline.py** (854 lines, 24 classes):
   - Move HTTP configs → `http.py`: `HttpClientConfig`, `ProviderHttpConfig`
   - Move quality configs → `quality.py`: `DeterminismConfig`, `QualityControlConfig`, `CanonicalizationConfig`, `BusinessKeyConfig`, `HashingConfig`
   - Move observability → `observability.py`: `LoggingConfig`, `MetricsConfig`, `ObservabilityConfig`
   - Move provider configs → `providers.py`: `BaseProviderConfig`, `ChemblSourceConfig`, `DummyProviderConfig`, `ProviderConfigUnion`
   - Keep in pipeline.py: `PipelineConfig`, `RuntimeConfig`, `PipelineStagesConfig`, `FeatureFlagsConfig`, `StorageConfig`, `PaginationConfig`

2. **Remove base.py**:
   - It's a legacy compatibility layer that re-exports everything from pipeline.py
   - Update imports to use `__init__.py` or direct module imports

3. **Deprecate pipeline_parts.py**:
   - Classes are not exported or used externally
   - Either integrate into main config classes or remove

### Medium Priority

4. **Consolidate defaults.py**:
   - Consider moving to infrastructure layer (these are runtime defaults)

5. **Verify ProfileConfig usage**:
   - No external imports found
   - May be dead code or internally used only

### Low Priority

6. **Remove deprecated aliases in v3.0**:
   - `ClientConfig`, `HttpClientSettings`, `HttpClientDefaults`, `HTTP_CLIENT_DEFAULTS`
   - Already emitting DeprecationWarning

---

## Migration Checklist

When refactoring, ensure:

- [ ] All 32 external consumer files are updated
- [ ] All 28 test files pass
- [ ] `tests/conftest.py` fixtures still work
- [ ] `__init__.py` exports remain backward compatible
- [ ] Deprecation warnings are added for moved classes
- [ ] TYPE_CHECKING imports are preserved to avoid cycles
