# Domain Ports

Port interfaces define contracts that infrastructure adapters must implement. All ports use Python's `Protocol` for structural typing.

## Storage & Data Access

### StoragePort

Main storage interface for writing data to all Medallion layers.

::: bioetl.domain.ports.StoragePort
    options:
        show-root-heading: true
        show-source: false

### DeltaReaderPort

Interface for read-only access to Delta tables.

::: bioetl.domain.ports.DeltaReaderPort
    options:
        show-root-heading: true
        show-source: false

### DataSourcePort

Interface for fetching data from external APIs.

::: bioetl.domain.ports.DataSourcePort
    options:
        show-root-heading: true
        show-source: false

### FilterableDataSourcePort

Extended interface for data sources supporting server-side filtering.

::: bioetl.domain.ports.FilterableDataSourcePort
    options:
        show-root-heading: true
        show-source: false

### IDMappingPort

Interface for ID mapping operations (e.g., UniProt mapping).

::: bioetl.domain.ports.IDMappingPort
    options:
        show-root-heading: true
        show-source: false

## Infrastructure Coordination

### LockPort

Distributed locking interface for pipeline coordination.

::: bioetl.domain.ports.LockPort
    options:
        show-root-heading: true
        show-source: false

### CheckpointPort

Pipeline state persistence interface.

::: bioetl.domain.ports.CheckpointPort
    options:
        show-root-heading: true
        show-source: false

### QuarantinePort

Dead-letter queue for failed records.

::: bioetl.domain.ports.QuarantinePort
    options:
        show-root-heading: true
        show-source: false

### ShutdownPort

Graceful termination coordination interface.

::: bioetl.domain.ports.ShutdownPort
    options:
        show-root-heading: true
        show-source: false

### AuditPort

Interface for write operation traceability.

::: bioetl.domain.ports.AuditPort
    options:
        show-root-heading: true
        show-source: false

### MetadataWriterPort

Interface for writing metadata.

::: bioetl.domain.ports.MetadataWriterPort
    options:
        show-root-heading: true
        show-source: false

### MetadataCoordinatorPort

Interface for coordinating metadata operations.

::: bioetl.domain.ports.MetadataCoordinatorPort
    options:
        show-root-heading: true
        show-source: false

## Observability

### MetricsPort

Prometheus-compatible metrics interface.

::: bioetl.domain.ports.MetricsPort
    options:
        show-root-heading: true
        show-source: false

### TracingPort

Distributed tracing interface (OpenTelemetry compatible).

::: bioetl.domain.ports.TracingPort
    options:
        show-root-heading: true
        show-source: false

### LoggerPort

Structured logging interface.

::: bioetl.domain.ports.LoggerPort
    options:
        show-root-heading: true
        show-source: false

### DQMonitorPort

Interface for monitoring data quality anomalies.

::: bioetl.domain.ports.DQMonitorPort
    options:
        show-root-heading: true
        show-source: false

### MemoryMonitorPort

Interface for monitoring memory usage.

::: bioetl.domain.ports.MemoryMonitorPort
    options:
        show-root-heading: true
        show-source: false

### HealthCheckPort

Interface for component health checks.

::: bioetl.domain.ports.HealthCheckPort
    options:
        show-root-heading: true
        show-source: false

### HealthMonitorPort

Interface for monitoring system health.

::: bioetl.domain.ports.HealthMonitorPort
    options:
        show-root-heading: true
        show-source: false

### HealthStatePort

Protocol for provider health state (read-only view).

::: bioetl.domain.ports.HealthStatePort
    options:
        show-root-heading: true
        show-source: false

### HealthCheckResult

Detailed result of a health check operation.

::: bioetl.domain.ports.HealthCheckResult
    options:
        show-root-heading: true
        show-source: false

## Security

### PiiHasherPort

Interface for hashing PII (Personal Identifiable Information) fields.

::: bioetl.domain.ports.PiiHasherPort
    options:
        show-root-heading: true
        show-source: false

## Resilience

### CircuitBreakerPort

Interface for circuit breaker pattern.

::: bioetl.domain.ports.CircuitBreakerPort
    options:
        show-root-heading: true
        show-source: false

### RateLimiterPort

Interface for rate limiting.

::: bioetl.domain.ports.RateLimiterPort
    options:
        show-root-heading: true
        show-source: false

## Data Quality & Validation

### GoldValidatorPort

Schema validation interface for Gold layer.

::: bioetl.domain.ports.GoldValidatorPort
    options:
        show-root-heading: true
        show-source: false

### SilverValidatorPort

Schema validation interface for Silver layer.

::: bioetl.domain.ports.SilverValidatorPort
    options:
        show-root-heading: true
        show-source: false

### DQReportWriterPort

Interface for writing DQ reports.

::: bioetl.domain.ports.DQReportWriterPort
    options:
        show-root-heading: true
        show-source: false

### BronzeDQAnalyzerPort

Interface for analyzing Bronze layer data quality.

::: bioetl.domain.ports.BronzeDQAnalyzerPort
    options:
        show-root-heading: true
        show-source: false

### SilverDQAnalyzerPort

Interface for analyzing Silver layer data quality.

::: bioetl.domain.ports.SilverDQAnalyzerPort
    options:
        show-root-heading: true
        show-source: false

### GoldDQAnalyzerPort

Interface for analyzing Gold layer data quality.

::: bioetl.domain.ports.GoldDQAnalyzerPort
    options:
        show-root-heading: true
        show-source: false

### BronzeDQConfigPort

Interface for Bronze DQ configuration.

::: bioetl.domain.ports.BronzeDQConfigPort
    options:
        show-root-heading: true
        show-source: false

### SilverDQConfigPort

Interface for Silver DQ configuration.

::: bioetl.domain.ports.SilverDQConfigPort
    options:
        show-root-heading: true
        show-source: false

### GoldDQConfigPort

Interface for Gold DQ configuration.

::: bioetl.domain.ports.GoldDQConfigPort
    options:
        show-root-heading: true
        show-source: false

## Transformation & Normalization

### NormalizationServicePort

Interface for normalization services.

::: bioetl.domain.ports.NormalizationServicePort
    options:
        show-root-heading: true
        show-source: false

### DataNormalizationPort

Interface for general data normalization.

::: bioetl.domain.ports.DataNormalizationPort
    options:
        show-root-heading: true
        show-source: false

### UnitConverterPort

Interface for unit conversion.

::: bioetl.domain.ports.UnitConverterPort
    options:
        show-root-heading: true
        show-source: false

### ValueValidatorPort

Interface for value validation.

::: bioetl.domain.ports.ValueValidatorPort
    options:
        show-root-heading: true
        show-source: false

### ActivityAggregatorPort

Interface for activity aggregation.

::: bioetl.domain.ports.ActivityAggregatorPort
    options:
        show-root-heading: true
        show-source: false

### OutlierFilterPort

Interface for filtering outliers.

::: bioetl.domain.ports.OutlierFilterPort
    options:
        show-root-heading: true
        show-source: false

### InputFilterPort

Interface for loading filter IDs from external sources.

::: bioetl.domain.ports.InputFilterPort
    options:
        show-root-heading: true
        show-source: false

### JsonEncoderPort

Interface for JSON encoding.

::: bioetl.domain.ports.JsonEncoderPort
    options:
        show-root-heading: true
        show-source: false

## Runner

### RunnablePort

Interface for runnable components.

::: bioetl.domain.ports.RunnablePort
    options:
        show-root-heading: true
        show-source: false

### RunnerFactoryPort

Interface for creating runners.

::: bioetl.domain.ports.RunnerFactoryPort
    options:
        show-root-heading: true
        show-source: false

### MetricsExtractorPort

Interface for extracting metrics from runners.

::: bioetl.domain.ports.MetricsExtractorPort
    options:
        show-root-heading: true
        show-source: false

## Supporting Types

### AuditEntry

Data class for audit log entries.

::: bioetl.domain.ports.AuditEntry
    options:
        show-root-heading: true
        show-source: false

### AuditLayer

Enumeration for audit layer types (BRONZE, SILVER, GOLD).

::: bioetl.domain.ports.AuditLayer
    options:
        show-root-heading: true
        show-source: false

### AuditOperation

Enumeration for audit operation types (WRITE, DELETE, VACUUM).

::: bioetl.domain.ports.AuditOperation
    options:
        show-root-heading: true
        show-source: false

### MemoryStats

Data class for memory usage statistics.

::: bioetl.domain.ports.MemoryStats
    options:
        show-root-heading: true
        show-source: false

## Metadata Types

### MetadataCoordinatorPort Inputs

Supporting types for `MetadataCoordinatorPort`:

::: bioetl.domain.ports.BronzeMetadataInput
    options:
        show-root-heading: true
        show-source: false

::: bioetl.domain.ports.SilverMetadataInput
    options:
        show-root-heading: true
        show-source: false

::: bioetl.domain.ports.GoldMetadataInput
    options:
        show-root-heading: true
        show-source: false

::: bioetl.domain.ports.SilverRef
    options:
        show-root-heading: true
        show-source: false

## NoOp Implementations

Null Object Pattern implementations for optional observability components.
These allow domain/application code to work without depending on concrete implementations.

### NoOpTracing

No-operation implementation of `TracingPort`.

::: bioetl.domain.ports.NoOpTracing
    options:
        show-root-heading: true
        show-source: false

### NoOpMetrics

No-operation implementation of `MetricsPort`.

::: bioetl.domain.ports.NoOpMetrics
    options:
        show-root-heading: true
        show-source: false

### NoOpAudit

No-operation implementation of `AuditPort`.

::: bioetl.domain.ports.NoOpAudit
    options:
        show-root-heading: true
        show-source: false

### NoOpMemoryMonitor

No-operation implementation of `MemoryMonitorPort`.

::: bioetl.domain.ports.NoOpMemoryMonitor
    options:
        show-root-heading: true
        show-source: false

### NoOpMetadataWriter

No-operation implementation of `MetadataWriterPort`.

::: bioetl.domain.ports.NoOpMetadataWriter
    options:
        show-root-heading: true
        show-source: false

### NoOpPiiHasher

No-operation implementation of `PiiHasherPort`.

::: bioetl.domain.ports.NoOpPiiHasher
    options:
        show-root-heading: true
        show-source: false

## Usage Example

```python
from bioetl.domain.ports import StoragePort, DataSourcePort

# Ports are structural types (Protocols)
async def process-data(
    source: DataSourcePort,
    storage: StoragePort,
) -> None:
    async for records in source.fetch():
        await storage.write-bronze(records, ...)
```

```python
# Using NoOp implementations for testing
from bioetl.domain.ports import NoOpTracing, NoOpMetrics

tracer = NoOpTracing()
metrics = NoOpMetrics()

# These can be passed where TracingPort/MetricsPort are expected
# without any external dependencies
```

## See Also

- [Types](types.md) - Core type definitions
- [Infrastructure Adapters](../infrastructure/adapters.md) - Port implementations
