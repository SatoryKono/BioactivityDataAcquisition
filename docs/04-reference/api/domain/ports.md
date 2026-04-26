______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-14'

______________________________________________________________________

# Domain Layer Ports Reference

## Overview

This document provides a comprehensive reference for all ports in the BioETL domain layer. Ports define the interfaces that the domain layer exposes to other layers, following the Hexagonal Architecture pattern.

## Port Categories

### Core Domain Ports

#### Data Source Ports

- **`DataSourcePort`** (`data_source.py`) - Primary interface for data retrieval
- **`DeltaReaderPort`** (`delta_reader.py`) - Interface for reading Delta Lake tables
- **`ExportPort`** (`export.py`) - Interface for data export operations

#### Processing Ports

- **`FilteringPort`** (`filtering.py`) - Interface for data filtering operations
- **`DataNormalizationPort`** (`data_normalization.py`) - Interface for data normalization
- **`IDMappingPort`** (`idmapping.py`) - Interface for ID mapping operations

#### Storage Ports

- **`StoragePort`** (`storage/`) - Base storage interface
- **`BronzeStoragePort`** (`storage/bronze_port.py`) - Bronze layer storage
- **`SilverStoragePort`** (`storage/silver_port.py`) - Silver layer storage
- **`GoldStoragePort`** (`storage/gold_port.py`) - Gold layer storage
- **`StorageMaintenancePort`** (`storage_maintenance.py`) - Storage maintenance operations

#### Observability Ports

- **`LoggerPort`** (`logger_port.py`) - Logging interface
- **`MetricsPort`** (`metrics_port.py`) - Metrics collection interface
- **`ObservabilityPort`** (`observability/`) - Comprehensive observability interface

#### Quality Control Ports

- **`QualityPort`** (`quality/`) - Data quality interface
- **`PIIPort`** (`pii.py`) - PII handling interface
- **`AuditPort`** (`audit.py`) - Auditing interface

#### Runtime Ports

- **`RuntimePort`** (`runtime/`) - Runtime control interface
- **`ResiliencePort`** (`resilience.py`) - Resilience and retry interface
- **`HealthCheckPort`** (`health_check.py`) - Health checking interface

#### Configuration Ports

- **`ConfigPort`** (`config/`) - Configuration interface
- **`MetadataPort`** (`metadata/`) - Metadata management interface
- **`ControlPlanePort`** (`control_plane/`) - Control plane operations

#### Specialized Ports

- **`SerializationPort`** (`serialization.py`) - Data serialization interface
- **`PublicationStrategyPort`** (`publication_strategy.py`) - Publication strategy interface
- **`ADRPort`** (`adr.py`) - Architecture Decision Record interface

## Port Details

### DataSourcePort

**Location**: `src/bioetl/domain/ports/data_source.py`
**Purpose**: Primary interface for retrieving data from external sources
**Key Methods**:

- `fetch_data(query: DataQuery) -> DataFrame`
- `fetch_batch(queries: List[DataQuery]) -> List[DataFrame]`
- `get_schema(source: str) -> Schema`

### StoragePort

**Location**: `src/bioetl/domain/ports/storage/`
**Purpose**: Base interface for all storage operations
**Implementations**:

- `BronzeStoragePort` - Raw data storage
- `SilverStoragePort` - Normalized data storage
- `GoldStoragePort` - Aggregated data storage

**Key Methods**:

- `write(data: DataFrame, partition_spec: Dict) -> WriteResult`
- `read(filter: Optional[Filter] = None) -> DataFrame`
- `update(data: DataFrame, condition: Filter) -> UpdateResult`
- `delete(condition: Filter) -> DeleteResult`

### LoggerPort

**Location**: `src/bioetl/domain/ports/logger_port.py`
**Purpose**: Structured logging interface
**Key Methods**:

- `info(message: str, context: Dict = None)`
- `warning(message: str, context: Dict = None)`
- `error(message: str, context: Dict = None, exception: Exception = None)`
- `debug(message: str, context: Dict = None)`

### MetricsPort

**Location**: `src/bioetl/domain/ports/metrics_port.py`
**Purpose**: Metrics collection and reporting
**Key Methods**:

- `increment(counter: str, value: int = 1, tags: Dict = None)`
- `gauge(metric: str, value: float, tags: Dict = None)`
- `timing(metric: str, duration: float, tags: Dict = None)`
- `histogram(metric: str, value: float, tags: Dict = None)`

## Usage Patterns

### Dependency Injection

All ports should be injected via constructors:

```python
from bioetl.domain.ports import DataSourcePort


class MyService:
    def __init__(self, data_source: DataSourcePort):
        self.data_source = data_source
```

### Port Implementation

Infrastructure layer provides concrete implementations:

```python
from bioetl.domain.ports import StoragePort
from bioetl.infrastructure.adapters import DeltaLakeAdapter


class DeltaStorage(StoragePort):
    def __init__(self, adapter: DeltaLakeAdapter):
        self.adapter = adapter

    def write(self, data: DataFrame, partition_spec: Dict) -> WriteResult:
        # Implementation using Delta Lake
        pass
```

## Governance

- **Naming**: All ports must end with `Port` suffix
- **Location**: Ports must be defined in `src/bioetl/domain/ports/`
- **Documentation**: Each port must have docstring with purpose and key methods
- **Testing**: Ports must have interface tests in `tests/unit/domain/ports/`

## Related Documents

- [Hexagonal Architecture](../../../02-architecture/decisions/ADR-005-composition-layer-separation.md)
- [Domain Layer Design](../../../02-architecture/01-domain-layer.md)
- [Ports and Adapters Pattern](../../../02-architecture/00-overview.md#ports-adapters)
