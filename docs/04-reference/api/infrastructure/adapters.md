# Infrastructure Adapters

Implementations of domain ports for external systems.

## HTTP Adapters

### UnifiedHTTPClient

Unified HTTP client with rate limiting, circuit breaker, and observability.

::: bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - get
            - post
            - head

### TokenBucket

Token bucket rate limiter implementation.

::: bioetl.infrastructure.adapters.http.rate_limiter.TokenBucket
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - acquire
            - try_acquire
            - available_tokens

### CircuitBreaker

Circuit breaker pattern implementation.

::: bioetl.infrastructure.adapters.http.circuit_breaker.CircuitBreaker
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - call
            - state

### PaginatedFetcherMixin

Mixin for handling paginated API responses.

::: bioetl.infrastructure.adapters.http.pagination.PaginatedFetcherMixin
    options:
        show_root_heading: true
        show_source: false
        members:
            - fetch_all_pages

## Base Adapters

### BaseHttpAdapter

Abstract base class for HTTP-based data source adapters.

::: bioetl.infrastructure.adapters.base.BaseHttpAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

### BaseSyncAdapter

Base class for synchronous data source adapters (e.g., PubChem via pubchempy).

::: bioetl.infrastructure.adapters.sync_base.BaseSyncAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - fetch
            - _run_in_executor

### AdapterMetrics

Metrics collection for data source adapters.

::: bioetl.infrastructure.adapters.base_metrics.AdapterMetrics
    options:
        show_root_heading: true
        show_source: false

## Provider Adapters

### ChemblAdapter

Data source adapter for ChEMBL database.

::: bioetl.infrastructure.adapters.chembl.client.ChemblAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Async HTTP requests with rate limiting
- Entity mapping via `EntityMapper`
- Circuit breaker integration
- Structured error classification

### PubChemAdapter

Data source adapter for PubChem database (via pubchempy library).

::: bioetl.infrastructure.adapters.pubchem.client.PubChemAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Sync library wrapped with `run_in_executor`
- Rate limiting (5 req/sec)
- Compound property extraction

### UniProtAdapter

Data source adapter for UniProt protein database.

::: bioetl.infrastructure.adapters.uniprot.client.UniProtAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Paginated fetching via `PaginatedFetcherMixin`
- ID mapping support
- Rate limiting (100 req/sec with API key)

### UniProtIDMappingClient

Specialized client for UniProt ID mapping operations.

::: bioetl.infrastructure.adapters.uniprot.idmapping_client.UniProtIDMappingClient
    options:
        show_root_heading: true
        show_source: false

### PubMedAdapter

Data source adapter for PubMed/NCBI E-utilities.

::: bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- ESearch/EFetch API integration
- Rate limiting (3 req/sec)
- XML response parsing

### CrossRefAdapter

Data source adapter for CrossRef metadata API.

::: bioetl.infrastructure.adapters.crossref.client.CrossRefAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Polite pool rate limiting
- DOI-based lookups
- Works endpoint integration

### OpenAlexAdapter

Data source adapter for OpenAlex scholarly data API.

::: bioetl.infrastructure.adapters.openalex.client.OpenAlexAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Rate limiting (10 req/sec)
- Cursor-based pagination
- Rich metadata extraction

### SemanticScholarAdapter

Data source adapter for Semantic Scholar API.

::: bioetl.infrastructure.adapters.semanticscholar.adapter.SemanticScholarAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - fetch
            - health_check

**Features**:
- Rate limiting (100 req/5min)
- Paper and author endpoints
- Citation graph access

## Storage Adapters

### SilverWriter

Storage adapter for Delta Lake (Silver layer).

> **Note**: `DeltaWriter` is deprecated and will be removed after a 14-day deprecation period. Use `SilverWriter` instead.

::: bioetl.infrastructure.storage.silver_writer.SilverWriter
    options:
        show_root_heading: true
        show_source: false
        members:
            - write_silver
            - vacuum
            - optimize
            - get_table_info

### BronzeWriter

Storage adapter for local filesystem (Bronze layer).

::: bioetl.infrastructure.storage.bronze_writer.BronzeWriter
    options:
        show_root_heading: true
        show_source: false
        members:
            - write_bronze
            - list_files

## Lock Adapters

### MemoryLock

In-memory lock implementation (Local-Only).

::: bioetl.infrastructure.locking.memory_lock.MemoryLock
    options:
        show_root_heading: true
        show_source: false
        members:
            - acquire
            - release
            - heartbeat

## Checkpoint Adapters

### LocalCheckpoint

Local filesystem checkpoint implementation.

::: bioetl.infrastructure.checkpoint.local_checkpoint.LocalCheckpoint
    options:
        show_root_heading: true
        show_source: false
        members:
            - save
            - load
            - delete

## Observability

Observability components are documented in [Observability](observability.md).

## Usage Example

```python
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

# Create rate limiter
limiter = TokenBucket(rate=5.0, capacity=10)

# Create client
client = UnifiedHTTPClient(
    rate_limiter=limiter,
    provider="chembl",
)

# Make request
response = await client.get("https://www.ebi.ac.uk/chembl/api/data/activity")
```

## See Also

- [Domain Ports](../domain/ports.md) - Interfaces implemented by adapters
