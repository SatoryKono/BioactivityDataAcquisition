# Domain Ports

Port interfaces define contracts that infrastructure adapters must implement. All ports use Python's `Protocol` for structural typing.

## Storage & Data Access

### StoragePort

Main storage interface for writing data to all Medallion layers.

::: bioetl.domain.ports.StoragePort
    options:
        show_root_heading: true
        show_source: false

### DeltaReaderPort

Interface for read-only access to Delta tables.

::: bioetl.domain.ports.DeltaReaderPort
    options:
        show_root_heading: true
        show_source: false

### DataSourcePort

Interface for fetching data from external APIs.

::: bioetl.domain.ports.DataSourcePort
    options:
        show_root_heading: true
        show_source: false

### FilterableDataSourcePort

Extended interface for data sources supporting server-side filtering.

::: bioetl.domain.ports.FilterableDataSourcePort
    options:
        show_root_heading: true
        show_source: false

### IDMappingPort

Interface for ID mapping operations (e.g., UniProt mapping).

::: bioetl.domain.ports.IDMappingPort
    options:
        show_root_heading: true
        show_source: false

## Infrastructure Coordination

### LockPort

Distributed locking interface for pipeline coordination.

::: bioetl.domain.ports.LockPort
    options:
        show_root_heading: true
        show_source: false

### CheckpointPort

Pipeline state persistence interface.

::: bioetl.domain.ports.CheckpointPort
    options:
        show_root_heading: true
        show_source: false

### QuarantinePort

Dead-letter queue for failed records.

::: bioetl.domain.ports.QuarantinePort
    options:
        show_root_heading: true
        show_source: false

### ShutdownPort

Graceful termination coordination interface.

::: bioetl.domain.ports.ShutdownPort
    options:
        show_root_heading: true
        show_source: false

### AuditPort

Interface for write operation traceability.

::: bioetl.domain.ports.AuditPort
    options:
        show_root_heading: true
        show_source: false

### MetadataWriterPort

Interface for writing metadata.

::: bioetl.domain.ports.MetadataWriterPort
    options:
        show_root_heading: true
        show_source: false

### MetadataCoordinatorPort

Interface for coordinating metadata operations.

::: bioetl.domain.ports.MetadataCoordinatorPort
    options:
        show_root_heading: true
        show_source: false

## Observability

### MetricsPort

Prometheus-compatible metrics interface.

::: bioetl.domain.ports.MetricsPort
    options:
        show_root_heading: true
        show_source: false

### TracingPort

Distributed tracing interface (OpenTelemetry compatible).

::: bioetl.domain.ports.TracingPort
    options:
        show_root_heading: true
        show_source: false

### LoggerPort

Structured logging interface.

::: bioetl.domain.ports.LoggerPort
    options:
        show_root_heading: true
        show_source: false

### DQMonitorPort

Interface for monitoring data quality anomalies.

::: bioetl.domain.ports.DQMonitorPort
    options:
        show_root_heading: true
        show_source: false

### MemoryMonitorPort

Interface for monitoring memory usage.

::: bioetl.domain.ports.MemoryMonitorPort
    options:
        show_root_heading: true
        show_source: false

### HealthCheckPort

Interface for component health checks.

::: bioetl.domain.ports.HealthCheckPort
    options:
        show_root_heading: true
        show_source: false

### HealthMonitorPort

Interface for monitoring system health.

::: bioetl.domain.ports.HealthMonitorPort
    options:
        show_root_heading: true
        show_source: false

## Resilience

### CircuitBreakerPort

Interface for circuit breaker pattern.

::: bioetl.domain.ports.CircuitBreakerPort
    options:
        show_root_heading: true
        show_source: false

### RateLimiterPort

Interface for rate limiting.

::: bioetl.domain.ports.RateLimiterPort
    options:
        show_root_heading: true
        show_source: false

## Data Quality & Validation

### GoldValidatorPort

Schema validation interface for Gold layer.

::: bioetl.domain.ports.GoldValidatorPort
    options:
        show_root_heading: true
        show_source: false

### SilverValidatorPort

Schema validation interface for Silver layer.

::: bioetl.domain.ports.SilverValidatorPort
    options:
        show_root_heading: true
        show_source: false

### DQReportWriterPort

Interface for writing DQ reports.

::: bioetl.domain.ports.DQReportWriterPort
    options:
        show_root_heading: true
        show_source: false

### BronzeDQAnalyzerPort

Interface for analyzing Bronze layer data quality.

::: bioetl.domain.ports.BronzeDQAnalyzerPort
    options:
        show_root_heading: true
        show_source: false

### SilverDQAnalyzerPort

Interface for analyzing Silver layer data quality.

::: bioetl.domain.ports.SilverDQAnalyzerPort
    options:
        show_root_heading: true
        show_source: false

### GoldDQAnalyzerPort

Interface for analyzing Gold layer data quality.

::: bioetl.domain.ports.GoldDQAnalyzerPort
    options:
        show_root_heading: true
        show_source: false

### BronzeDQConfigPort

Interface for Bronze DQ configuration.

::: bioetl.domain.ports.BronzeDQConfigPort
    options:
        show_root_heading: true
        show_source: false

### SilverDQConfigPort

Interface for Silver DQ configuration.

::: bioetl.domain.ports.SilverDQConfigPort
    options:
        show_root_heading: true
        show_source: false

### GoldDQConfigPort

Interface for Gold DQ configuration.

::: bioetl.domain.ports.GoldDQConfigPort
    options:
        show_root_heading: true
        show_source: false

## Transformation & Normalization

### NormalizationServicePort

Interface for normalization services.

::: bioetl.domain.ports.NormalizationServicePort
    options:
        show_root_heading: true
        show_source: false

### DataNormalizationPort

Interface for general data normalization.

::: bioetl.domain.ports.DataNormalizationPort
    options:
        show_root_heading: true
        show_source: false

### UnitConverterPort

Interface for unit conversion.

::: bioetl.domain.ports.UnitConverterPort
    options:
        show_root_heading: true
        show_source: false

### ValueValidatorPort

Interface for value validation.

::: bioetl.domain.ports.ValueValidatorPort
    options:
        show_root_heading: true
        show_source: false

### ActivityAggregatorPort

Interface for activity aggregation.

::: bioetl.domain.ports.ActivityAggregatorPort
    options:
        show_root_heading: true
        show_source: false

### OutlierFilterPort

Interface for filtering outliers.

::: bioetl.domain.ports.OutlierFilterPort
    options:
        show_root_heading: true
        show_source: false

### InputFilterPort

Interface for loading filter IDs from external sources.

::: bioetl.domain.ports.InputFilterPort
    options:
        show_root_heading: true
        show_source: false

### JsonEncoderPort

Interface for JSON encoding.

::: bioetl.domain.ports.JsonEncoderPort
    options:
        show_root_heading: true
        show_source: false

## Runner

### RunnablePort

Interface for runnable components.

::: bioetl.domain.ports.RunnablePort
    options:
        show_root_heading: true
        show_source: false

### RunnerFactoryPort

Interface for creating runners.

::: bioetl.domain.ports.RunnerFactoryPort
    options:
        show_root_heading: true
        show_source: false

### MetricsExtractorPort

Interface for extracting metrics from runners.

::: bioetl.domain.ports.MetricsExtractorPort
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.domain.ports import StoragePort, DataSourcePort

# Ports are structural types (Protocols)
async def process_data(
    source: DataSourcePort,
    storage: StoragePort,
) -> None:
    async for records in source.fetch():
        await storage.write_bronze(records, ...)
```

## See Also

- [Types](types.md) - Core type definitions
- [Infrastructure Adapters](../infrastructure/adapters.md) - Port implementations
