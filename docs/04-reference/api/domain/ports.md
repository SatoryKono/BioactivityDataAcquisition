______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-20'

______________________________________________________________________

# Domain Layer Ports Reference

## Scope

This page documents the live public port surface exported by
`src/bioetl/domain/ports/__init__.py`. It is a maintained family reference,
not a method-by-method mirror of every protocol.

For exact signatures, use the source modules under `src/bioetl/domain/ports/`.
For architectural rationale, use ADR-005, ADR-006, ADR-017, ADR-044, and
ADR-047.

## Canonical Public Export

- Canonical import surface: `from bioetl.domain import ports`
- Public export registry: `src/bioetl/domain/ports/__init__.py`
- Port source tree: `src/bioetl/domain/ports/`

The domain layer currently exposes focused port families rather than a small
set of umbrella protocols. Do not document fictional catch-all interfaces such
as `StoragePort`, `ObservabilityPort`, `RuntimePort`, or `ControlPlanePort`
unless they exist in the live public export.

## Live Port Families

### Data Acquisition

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Source fetching | `DataSourcePort`, `FilterableDataSourcePort`, `DataSourceFactoryPort` | `data_source.py` |
| Delta reads | `DeltaReaderPort` | `delta_reader.py` |
| Export writing | `ExportWriterPort`, `ExportCatalogPort` | `export.py` |
| Input filtering | `InputFilterPort` | `filtering.py` |
| ID mapping | `IDMappingPort`, `IDMappingSourceReaderPort` | `idmapping.py` |
| Normalization strategy | `DataNormalizationPort` | `data_normalization.py` |

### Storage And Output

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Medallion storage | `BronzeStoragePort`, `SilverStoragePort`, `GoldStoragePort`, `MergedStoragePort` | `storage/` |
| Storage lifecycle | `StorageLifecyclePort`, `StorageMaintenancePort` | `storage/`, `storage_maintenance.py` |
| Silver write payload | `SilverWriteRequest`, `coerce_silver_write_request` | `storage/` |
| Serialization | `JsonEncoderPort` | `serialization.py` |

### Observability And Health

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Logging and metrics | `LoggerPort`, `MetricsPort`, `MetricsPublisherPort`, `ExecutorMetricsPort` | `observability/` |
| Tracing | `TracingPort` | `observability/` |
| Metrics server | `MetricsServerPort`, `MetricsServerRuntimeStatus` | `observability/` |
| DQ monitoring | `DQMonitorPort` | `observability/` |
| Health | `HealthCheckPort`, `HealthMonitorPort`, `HealthStatePort` | `health_check.py` |

### Runtime Control

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Runner assembly | `RunnablePort`, `RunnerFactoryPort`, `PipelineFactoryPort`, `PipelineRegistryPort` | `runtime/` |
| Locking and checkpoints | `LockPort`, `CheckpointPort`, `CompositeCheckpointPort` | `runtime/` |
| Shutdown and clock | `ShutdownPort`, `ClockPort`, `BatchIdGeneratorPort` | `runtime/` |
| Runtime inspection | `PipelineDebugPort`, `PipelineSnapshot`, `ExecutionObservabilityPort` | `runtime/` |
| Memory/runtime telemetry | `MemoryMonitorPort`, `MemoryStats`, `MetricsExtractorPort` | `runtime/` |

### Control Plane And Reproducibility

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Run control plane | `RunManifestPort`, `RunLedgerPort`, `EffectiveConfigArtifactStorePort`, `LineageStorePort` | `control_plane/` |
| Workflow control plane | `WorkflowManifestPort`, `WorkflowLedgerPort`, `WorkflowExecutionStatePort` | `control_plane/` |
| Replay/audit helpers | `ArtifactByteComparisonPort` | `control_plane/` |

### Quality, Audit, And Compliance

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Silver/Gold validation | `SilverValidatorPort`, `GoldValidatorPort` | `quality/` |
| DQ analysis | `BronzeDQAnalyzerPort`, `SilverDQAnalyzerPort`, `GoldDQAnalyzerPort` | `quality/` |
| DQ configuration | `BronzeDQConfigPort`, `SilverDQConfigPort`, `GoldDQConfigPort` | `quality/` |
| Error handling | `ErrorClassifierPort`, `ErrorHandlerPort`, `FallbackPolicyPort` | `quality/` |
| Quarantine | `QuarantinePort`, `QuarantineWriteRequest` | `quality/` |
| Audit and PII | `AuditPort`, `PiiHasherPort` | `audit.py`, `pii.py` |

### Configuration, Metadata, And Strategy Surfaces

| Family | Representative exports | Canonical modules |
| --- | --- | --- |
| Settings/config loading | `SettingsPort`, `SettingsLoaderPort`, `PipelineSettingsPort`, `PipelineConfigLoaderPort`, `PipelineYamlConfigPort` | `config/` |
| Domain config mapping | `DomainConfigMapperPort` | `config/` |
| Metadata publication | `MetadataWriterPort`, `MetadataCoordinatorPort` | `metadata/` |
| Publication strategy seams | `PublicationMetadataStrategy`, `IdentifierResolverStrategy`, `DataExtractorStrategy` | `publication_strategy.py` |
| Workflow foreign-key reconciliation | `ForeignKeyReconciliationPort` | `workflow_foreign_key_reconciliation.py` |
| ADR service surface | `AdrServicePort` | `adr.py` |

## Representative Live Signatures

The source modules remain authoritative. A few representative examples:

- `DataSourcePort`: provider-scoped fetch protocol with async context manager
  support in `data_source.py`.
- `MetricsPort`: low-cardinality metric publication surface with histogram,
  counter, and gauge operations in `observability/metrics.py`.
- `RunManifestPort` and `RunLedgerPort`: persisted control-plane artifact
  storage seams aligned with ADR-044.
- `WorkflowManifestPort`, `WorkflowLedgerPort`, and
  `WorkflowExecutionStatePort`: workflow control-plane seams aligned with
  ADR-047.

## Usage Guidance

- Import ports through the public package surface when you need stable domain
  contracts:

```python
from bioetl.domain.ports import DataSourcePort, RunManifestPort
```

- When documenting or testing a single protocol, cite the concrete module that
  defines it instead of paraphrasing historical signatures from older docs.
- If a new port is added to `src/bioetl/domain/ports/__init__.py`, update this
  page in the same change set.

## Related Surfaces

- [Domain Layer](../../../02-architecture/01-domain-layer.md)
- [Application API](../application.md)
- [Infrastructure API](../infrastructure.md)
- [Run Manifest & Ledger Contract](../../contracts/run-manifest-ledger.md)
- [ADR-047 Workflow Control Plane](../../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
