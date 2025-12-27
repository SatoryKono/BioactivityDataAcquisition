# Infrastructure Layer

The Infrastructure layer contains concrete implementations of domain ports. It handles all I/O operations: HTTP clients, storage, metrics, logging.

## Overview

```mermaid
flowchart TB
    subgraph Infrastructure["Infrastructure Layer"]
        subgraph Adapters["Data Source Adapters"]
            ChEMBL[ChemblAdapter]
            PubChem[PubChemAdapter]
            UniProt[UniProtAdapter]
            PubMed[PubMedAdapter]
        end

        subgraph Storage["Storage Writers"]
            Bronze[BronzeWriter]
            Silver[DeltaWriter]
            Gold[GoldWriter]
        end

        subgraph Observability["Observability"]
            Metrics[MetricsExporter]
            Tracing[TracingExporter]
            Logging[StructlogLogger]
        end

        subgraph Support["Support"]
            Locking[MemoryLock]
            Checkpoint[LocalCheckpoint]
            Quarantine[UnifiedQuarantine]
        end
    end

    Adapters -.->|implements| DSPort["DataSourcePort"]
    Storage -.->|implements| SPort["StoragePort"]
    Observability -.->|implements| OPort["MetricsPort, TracingPort"]
    Support -.->|implements| LPort["LockPort, CheckpointPort"]
```

## Modules

### [Adapters](infrastructure/adapters.md)

Data source adapters implementing `DataSourcePort`:

- `ChemblAdapter` - ChEMBL database client
- `PubChemAdapter` - PubChem compound API
- `UniProtAdapter` - UniProt protein database
- `PubMedAdapter` - PubMed publication API
- `UnifiedHTTPClient` - Shared HTTP client infrastructure

### [Storage](infrastructure/storage.md)

Storage writers implementing `StoragePort`:

- `BronzeWriter` - JSONL + zstd compression
- `DeltaWriter` - Delta Lake Silver layer
- `GoldWriter` - Delta Lake Gold layer with SCD Type 2

### [Observability](infrastructure/observability.md)

Observability infrastructure:

- `PrometheusMetrics` - Prometheus metrics exporter
- `TracingExporter` - OpenTelemetry tracing
- `StructlogLogger` - Structured logging
- `LineageTracker` - Data lineage tracking

## Key Concepts

### Adapters vs Ports

| Domain Port | Infrastructure Adapter |
|-------------|----------------------|
| `DataSourcePort` | `ChemblAdapter`, `PubChemAdapter` |
| `StoragePort` | `BronzeWriter`, `DeltaWriter`, `GoldWriter` |
| `LockPort` | `MemoryLock` |
| `CheckpointPort` | `LocalCheckpoint` |
| `MetricsPort` | `PrometheusMetrics`, `NoOpMetrics` |
| `TracingPort` | `TracingExporter`, `NoOpTracing` |
| `LoggerPort` | `StructlogLogger`, `NoOpLogger` |

### Medallion Storage Layers

```mermaid
flowchart LR
    API["External API"] --> Bronze["Bronze<br/>(JSONL+zstd)"]
    Bronze --> Silver["Silver<br/>(Delta Lake)"]
    Silver --> Gold["Gold<br/>(Delta Lake)"]

    subgraph Formats
        B1["Raw JSON<br/>Append-only"]
        S1["Normalized<br/>Merge/Upsert"]
        G1["Validated<br/>SCD Type 2"]
    end

    Bronze --- B1
    Silver --- S1
    Gold --- G1
```

### Unified HTTP Client

All HTTP adapters use `UnifiedHTTPClient` for consistent behavior:

- Rate limiting (per-provider configuration)
- Circuit breaker pattern
- Retry with exponential backoff
- Request/response metrics
- Structured logging

```python
from bioetl.infrastructure.adapters.http import UnifiedHTTPClient

client = UnifiedHTTPClient(
    base_url="https://www.ebi.ac.uk/chembl/api/data",
    rate_limit=5.0,  # requests per second
    timeout=30.0,
    max_retries=3,
)
```

## Import Structure

```python
# Storage writers
from bioetl.infrastructure.storage import (
    BronzeWriter,
    DeltaWriter,
    GoldWriter,
)

# Data source adapters
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter

# HTTP infrastructure
from bioetl.infrastructure.adapters.http import UnifiedHTTPClient

# Observability
from bioetl.infrastructure.observability import PrometheusMetrics
from bioetl.infrastructure.observability.tracing import TracingExporter
```

## See Also

- [Adapters](infrastructure/adapters.md) - Data source adapters
- [Storage](infrastructure/storage.md) - Storage writers
- [Observability](infrastructure/observability.md) - Metrics, tracing, logging
- [Domain Ports](domain/ports.md) - Port interfaces
