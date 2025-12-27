# Data Source Adapters

Concrete implementations of `DataSourcePort` for external APIs.

## Overview

| Adapter | Provider | Rate Limit | Protocol |
|---------|----------|------------|----------|
| `ChemblAdapter` | ChEMBL | None | REST API |
| `PubChemAdapter` | PubChem | 5 req/sec | REST API |
| `UniProtAdapter` | UniProt | 100 req/sec | REST API |
| `PubMedAdapter` | PubMed/NCBI | 3 req/sec | E-utilities XML |

## HTTP Infrastructure

### UnifiedHTTPClient

Base HTTP client with rate limiting, retries, and circuit breaker.

::: bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - get
            - post
            - aclose

### RateLimiter

Token bucket rate limiter for API compliance.

::: bioetl.infrastructure.adapters.http.rate_limiter.RateLimiter
    options:
        show_root_heading: true
        show_source: false

### CircuitBreaker

Circuit breaker for failing fast on degraded services.

::: bioetl.infrastructure.adapters.http.circuit_breaker.CircuitBreaker
    options:
        show_root_heading: true
        show_source: false

## ChEMBL Adapter

### ChemblAdapter

ChEMBL database adapter with health-aware fetching.

::: bioetl.infrastructure.adapters.chembl.client.ChemblAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

### ChemblEntityMapper

Maps entity types to ChEMBL API endpoints.

::: bioetl.infrastructure.adapters.chembl.entity_mapper.ChemblEntityMapper
    options:
        show_root_heading: true
        show_source: false

## PubChem Adapter

### PubChemAdapter

PubChem compound data adapter using pubchempy library.

::: bioetl.infrastructure.adapters.pubchem.client.PubChemAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

## UniProt Adapter

### UniProtAdapter

UniProt protein database adapter.

::: bioetl.infrastructure.adapters.uniprot.client.UniProtAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

## PubMed Adapter

### PubMedAdapter

PubMed/NCBI E-utilities adapter for publication data.

::: bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

## Base Adapter Classes

### BaseHttpAdapter

Abstract base class for HTTP-based adapters.

::: bioetl.infrastructure.adapters.base.BaseHttpAdapter
    options:
        show_root_heading: true
        show_source: false

### BaseSyncAdapter

Base class for wrapping synchronous libraries.

::: bioetl.infrastructure.adapters.sync_base.BaseSyncAdapter
    options:
        show_root_heading: true
        show_source: false

## Health-Aware Fetching

Adapters adjust behavior based on health status:

| Status | Behavior |
|--------|----------|
| `HEALTHY` | Normal batch size |
| `DEGRADED` | batch_size ÷ 2 |
| `UNHEALTHY` | Fail fast with `CriticalError` |

```python
from bioetl.domain.types import HealthStatus

# Health check returns status
status = await adapter.health_check()

if status == HealthStatus.UNHEALTHY:
    raise CriticalError("ChEMBL API unavailable")
elif status == HealthStatus.DEGRADED:
    batch_size = batch_size // 2
```

## Usage Example

```python
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.http import UnifiedHTTPClient

# Create HTTP client with rate limiting
http_client = UnifiedHTTPClient(
    base_url="https://www.ebi.ac.uk/chembl/api/data",
    timeout=30.0,
    max_retries=3,
)

# Create ChEMBL adapter
adapter = ChemblAdapter(
    http_client=http_client,
    logger=logger,
    batch_size=1000,
)

# Health check before fetching
status = await adapter.health_check()
if status == HealthStatus.HEALTHY:
    async for batch in adapter.fetch(entity_type="activity"):
        process_batch(batch)

await adapter.aclose()
```

## See Also

- [Storage Writers](storage.md) - Storage layer implementations
- [Domain Ports](../domain/ports.md) - Port interfaces
- [Circuit Breaker ADR](../../../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md)
