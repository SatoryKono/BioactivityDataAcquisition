# Domain Ports

Port interfaces define contracts that infrastructure adapters must implement. All ports use Python's `Protocol` for structural typing.

## Storage Ports

### StoragePort

Main storage interface for writing data to all Medallion layers.

::: bioetl.domain.ports.StoragePort
    options:
        show_root_heading: true
        show_source: false
        members:
            - write_bronze
            - write_silver
            - write_gold
            - health_check
            - aclose

## Data Source Ports

### DataSourcePort

Interface for fetching data from external APIs.

::: bioetl.domain.ports.DataSourcePort
    options:
        show_root_heading: true
        show_source: false
        members:
            - fetch
            - health_check

### FilterableDataSourcePort

Extended interface for data sources supporting server-side filtering.

::: bioetl.domain.ports.FilterableDataSourcePort
    options:
        show_root_heading: true
        show_source: false

## Infrastructure Ports

### LockPort

Distributed locking interface for pipeline coordination.

::: bioetl.domain.ports.LockPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - acquire
            - release
            - refresh
            - is_held

### CheckpointPort

Pipeline state persistence interface.

::: bioetl.domain.ports.CheckpointPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - save
            - load
            - delete

### QuarantinePort

Dead-letter queue for failed records.

::: bioetl.domain.ports.QuarantinePort
    options:
        show_root_heading: true
        show_source: false
        members:
            - write
            - read
            - purge

## Observability Ports

### MetricsPort

Prometheus-compatible metrics interface.

::: bioetl.domain.ports.MetricsPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - increment_counter
            - set_gauge
            - observe_histogram
            - close

### TracingPort

Distributed tracing interface (OpenTelemetry compatible).

::: bioetl.domain.ports.TracingPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - get_tracer
            - close

### LoggerPort

Structured logging interface.

::: bioetl.domain.ports.LoggerPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - info
            - warning
            - error
            - debug
            - exception
            - bind

## Validation Ports

### GoldValidatorPort

Schema validation interface for Gold layer.

::: bioetl.domain.ports.GoldValidatorPort
    options:
        show_root_heading: true
        show_source: false

## Filtering Ports

### InputFilterPort

Interface for loading filter IDs from external sources.

::: bioetl.domain.ports.InputFilterPort
    options:
        show_root_heading: true
        show_source: false
        members:
            - load_filter_ids

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
