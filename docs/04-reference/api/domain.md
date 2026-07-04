______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-23'

______________________________________________________________________

# Domain Layer API Reference

This page documents the **current sanctioned public import surfaces** for the
BioETL domain layer.

Use it when you need the live Python-facing API boundaries. For semantic
catalogs and invariants, use the published domain reference set under
[`../domain/`](../domain/README.md).

## Import Policy

- `bioetl.domain` is a **slim lazy facade**. It does not re-export the entire
  domain tree.
- `bioetl.domain.context` is the sanctioned runtime-context facade.
- `bioetl.domain.ports` is the sanctioned port-contract facade.
- Internal modules under `src/bioetl/domain/**` may exist for structure and
  lazy loading, but callers should prefer the documented public facades.

## Top-Level `bioetl.domain` Facade

The top-level package currently exports the following live public symbols from
`src/bioetl/domain/__init__.py`:

### Event and observability exports

| Symbol | Source |
| --- | --- |
| `PipelineEvent` | `bioetl.domain.events` |
| `DomainEventObservabilityEnvelope` | `bioetl.domain.observability_event_mapping` |
| `map_domain_event_to_observability_event` | `bioetl.domain.observability_event_mapping` |
| `get_runtime_observability_publication_contract` | `bioetl.domain.runtime_observability_publication_contract` |
| `is_canonical_runtime_observability_emitter` | `bioetl.domain.runtime_observability_publication_contract` |
| `get_version` | `bioetl.domain.version` |

### Lazy submodule exports

| Symbol | Source module |
| --- | --- |
| `behavior` | `bioetl.domain.behavior` |
| `composite` | `bioetl.domain.composite` |
| `constants` | `bioetl.domain.constants` |
| `context_cached_bronze` | `bioetl.domain.context_cached_bronze` |
| `context_correlation` | `bioetl.domain.context_correlation` |
| `context_filtering` | `bioetl.domain.context_filtering` |
| `context_run` | `bioetl.domain.context_run` |
| `context_time` | `bioetl.domain.context_time` |
| `context_validation` | `bioetl.domain.context_validation` |
| `contracts` | `bioetl.domain.contracts` |
| `control_plane` | `bioetl.domain.control_plane` |
| `deterministic_identity` | `bioetl.domain.deterministic_identity` |
| `error_types` | `bioetl.domain.error_types` |
| `lineage` | `bioetl.domain.lineage` |
| `observability_contract` | `bioetl.domain.observability_contract` |
| `observability_event_mapping` | `bioetl.domain.observability_event_mapping` |
| `observability_metric_names` | `bioetl.domain.observability_metric_names` |
| `pubchem_standardization_catalog` | `bioetl.domain.pubchem_standardization_catalog` |
| `runtime_observability_publication_contract` | `bioetl.domain.runtime_observability_publication_contract` |
| `types_config_validation` | `bioetl.domain.types_config_validation` |
| `workflow` | `bioetl.domain.workflow` |

### Explicit non-exports

These surfaces are intentionally **not** part of `bioetl.domain.__all__` and
should be imported from their own facades/modules directly:

- `bioetl.domain.ports`
- `bioetl.domain.context`
- `bioetl.domain.types`
- `bioetl.domain.exceptions`
- `bioetl.domain.entities`
- `bioetl.domain.value_objects`

## Runtime Context Surface: `bioetl.domain.context`

`src/bioetl/domain/context.py` is the sanctioned facade for the runtime context
types carried through pipeline execution.

| Export | Purpose |
| --- | --- |
| `PipelineContext` | In-run processing context for record, batch, and write paths |
| `PipelineRunContext` | Launch-time execution descriptor and replay/control-plane anchor carrier |
| `CachedBronzeContext` | Cached-Bronze mode toggles and path/date anchors |
| `InputFilterContext` | Input-filter activation and filter-source metadata |
| `VacuumSettings` | Vacuum behavior options carried into runtime |
| `MISSING_RUNTIME_TIMESTAMP` | Deterministic sentinel for compatibility-only direct construction |

Live helper modules behind this surface:

| Module | Current responsibility |
| --- | --- |
| `bioetl.domain.context_run` | `PipelineRunContext` definition and invariants |
| `bioetl.domain.context_time` | `ClockLike`, `resolve_context_started_at()`, deterministic timestamp sentinel |
| `bioetl.domain.context_validation` | Contract-identity / DQ-compatibility validation helpers |
| `bioetl.domain.context_correlation` | correlation-field normalization helper |
| `bioetl.domain.context_filtering` | input-filter and vacuum option value objects |
| `bioetl.domain.context_cached_bronze` | cached Bronze replay/cache toggle value object |

For the published semantic catalog of these types, use
[Domain Contexts](../domain/contexts.md).

## Port Contract Surface: `bioetl.domain.ports`

`src/bioetl/domain/ports/__init__.py` is the sanctioned import facade for
transport-neutral contracts.

### Config ports

`DomainConfigMapperPort`, `PipelineConfigLoaderPort`,
`PipelineSettingsPort`, `PipelineYamlConfigPort`,
`PublicationVocabularyPort`, `SettingsLoaderPort`, `SettingsPort`

### Control-plane ports

`ArtifactByteComparisonPort`, `EffectiveConfigArtifactStorePort`,
`LineageStorePort`, `RunLedgerPort`, `RunManifestPort`,
`WorkflowExecutionStatePort`, `WorkflowLedgerPort`, `WorkflowManifestPort`

### Data-source and normalization ports

`DataSourceFactoryPort`, `DataSourcePort`, `FilterableDataSourcePort`,
`DataNormalizationPort`, `DeltaReaderPort`, `InputFilterPort`,
`IDMappingPort`, `IDMappingSourceReaderPort`,
`ProteinClassificationPort`

### Export and metadata ports

`ExportCatalogPort`, `ExportFileFingerprint`, `ExportWriterPort`,
`BronzeMetadataInput`, `GoldMetadataInput`, `MetadataCoordinatorPort`,
`MetadataWriterPort`, `SilverMetadataInput`, `SilverRef`

### Health and resilience ports

`HealthCheckPort`, `HealthCheckResult`, `HealthMonitorPort`,
`HealthStatePort`, `HealthStatusLiteral`, `CircuitBreakerPort`,
`RateLimiterPort`

### Observability ports

`DQMonitorPort`, `ExecutorMetricsPort`, `LoggerPort`, `MetricLabels`,
`MetricsPort`, `MetricsPublisherPort`, `MetricsServerPort`,
`MetricsServerRuntimeStatus`, `TracingPort`, `resolve_metric_labels`

### Quality ports

`BronzeDQAnalyzerPort`, `BronzeDQConfigPort`, `ContractPolicyProtocol`,
`DQReportWriterPort`, `ErrorClassifierPort`, `ErrorHandlerPort`,
`FallbackPolicyPort`, `GoldDQAnalyzerPort`, `GoldDQConfigPort`,
`GoldValidatorPort`, `QuarantinePort`, `QuarantineWriteRequest`,
`SilverDQAnalyzeRequest`, `SilverDQAnalyzerPort`, `SilverDQConfigPort`,
`SilverValidatorPort`, `coerce_silver_dq_analyze_request`

### Runtime ports

`BatchIdGeneratorPort`, `BreakpointHit`, `CheckpointPort`, `ClockPort`,
`CompositeCheckpointPort`, `DebugAction`, `ExecutionMetricsReadablePort`,
`ExecutionMetricsRunnerPort`, `ExecutionObservabilityPort`, `LockPort`,
`MemoryMonitorPort`, `MemoryStats`, `MetricsExtractorPort`,
`PipelineDebugPort`, `PipelineFactoryPort`, `PipelineRegistryPort`,
`PipelineSnapshot`, `RegistryAccessorPort`, `RunnablePort`,
`RunnerFactoryPort`, `ShutdownPort`, `StageBreakpoint`,
`MemoryDecisionTraceEntry`, `PipelineControlPlaneArtifacts`,
`PipelineCreateRunnerRequest`, `PipelineCreateWithServicesRequest`

### Storage ports

`BronzeStoragePort`, `GoldStoragePort`, `MergedStoragePort`,
`SilverStoragePort`, `SilverWriteRequest`, `StorageLifecyclePort`,
`StorageMaintenancePort`, `coerce_silver_write_request`

### Other flat port families

`AdrDocument`, `AdrInfo`, `AdrServicePort`, `AdrValidationIssue`,
`AdrValidationReport`, `AuditEntry`, `AuditLayer`, `AuditOperation`,
`AuditPort`, `PiiHasherPort`, `DataExtractorStrategy`,
`IdentifierResolverStrategy`, `PublicationMetadataStrategy`,
`JsonEncoderPort`, `ForeignKeyReconciliationPort`,
`ForeignKeyReconciliationRequest`, `ForeignKeyReconciliationResult`

## Validation Anchors

The public-facade expectations on this page are guarded by:

- `tests/architecture/test_domain_public_api.py`
- `tests/architecture/test_time_seam_normalization.py`

## Related References

- [Domain Reference](../domain/README.md)
- [Domain Contexts](../domain/contexts.md)
- [Domain Ports](../domain/ports.md)
- [API Reference: Domain Ports](domain/ports.md)
