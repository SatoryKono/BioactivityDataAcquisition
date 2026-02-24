# Infrastructure Adapters

Implementations of domain ports for external systems.

## HTTP Adapters

### UnifiedHTTPClient

Unified HTTP client with rate limiting, circuit breaker, and observability.

::: bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - get
            - post
            - head

### TokenBucket

Token bucket rate limiter implementation.

::: bioetl.infrastructure.adapters.http.rate_limiter.TokenBucket
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - acquire
            - try-acquire
            - available-tokens

### CircuitBreaker

Circuit breaker pattern implementation.

::: bioetl.infrastructure.adapters.http.circuit_breaker.CircuitBreaker
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - call
            - state

### PaginatedFetcherMixin

Mixin for handling paginated API responses.

::: bioetl.infrastructure.adapters.http.pagination.PaginatedFetcherMixin
    options:
        show-root-heading: true
        show-source: false
        members:
            - fetch-all-pages

## Base Adapters

### BaseHttpAdapter

Abstract base class for HTTP-based data source adapters.

::: bioetl.infrastructure.adapters.base.BaseHttpAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

### BaseSyncAdapter

Base class for synchronous data source adapters (e.g., PubChem via pubchempy).

::: bioetl.infrastructure.adapters.sync_base.BaseSyncAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - fetch
            - -run-in-executor

### AdapterMetrics

Metrics collection for data source adapters.

::: bioetl.infrastructure.adapters.base_metrics.AdapterMetrics
    options:
        show-root-heading: true
        show-source: false

## Provider Adapters

### ChemblAdapter

Data source adapter for ChEMBL database.

::: bioetl.infrastructure.adapters.chembl.client.ChemblAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Async HTTP requests with rate limiting
- Entity mapping via `ChemblEntityMapper`
- Circuit breaker integration
- Structured error classification
- Composite key deduplication for multi-PK entities
- Direct endpoint fallback for single-record failures

#### URL Formation

API URLs are constructed in `infrastructure/adapters/chembl/entity-mapper.py`:

| Component | Location | Example |
|-----------|----------|---------|
| Base URL | `CHEMBL-API-BASE` | `https://www.ebi.ac.uk/chembl/api/data` |
| Resource URL | `ChemblEntityMapper.get-resource-url()` | `/activity`, `/molecule`, `/target` |
| Direct record URL | `ChemblEntityMapper.get-direct-record-url()` | `/target/CHEMBL1075105` |
| Status endpoint | `CHEMBL-STATUS-URL` | `/status` |

**Entity to API resource mapping** (`-NON-PUBLICATION-ENTITY-MAPPING`):

| Entity Type | API Resource |
|-------------|--------------|
| `activity` | `activity` |
| `assay` | `assay` |
| `molecule`, `compound` | `molecule` |
| `target` | `target` |
| `target-component` | `target-component` |
| `cell-line` | `cell-line` |
| `compound-record` | `compound-record` |
| `protein-class` | `protein-classification` |
| `publication` | `document` (via domain registry) |

**Query parameters** (`ChemblAdapter.-build-params()`):

```python
params = {
    "format": "json",        # Required (ChEMBL no longer supports .json extension)
    "limit": batch-size,     # Health-aware: full/half depending on circuit breaker
    "offset": offset,        # Pagination offset
}
# Filter parameters: "{field}--in": "ID1,ID2,ID3"
```

**Configuration**: `configs/sources/chembl.yaml`

```yaml
source:
    provider-config:
        base-url: https://www.ebi.ac.uk/chembl/api/data
        page-size: 20
        batch-size: 20
    rate-limit:
        requests-per-second: 3
```

### PubChemAdapter

Data source adapter for PubChem database (via pubchempy library).

::: bioetl.infrastructure.adapters.pubchem.client.PubChemAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Sync library wrapped with `run-in-executor`
- Rate limiting (5 req/sec)
- Compound property extraction

### UniProtAdapter

Data source adapter for UniProt protein database.

::: bioetl.infrastructure.adapters.uniprot.client.UniProtAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Paginated fetching via `PaginatedFetcherMixin`
- ID mapping support
- Rate limiting (100 req/sec with API key)

### UniProtIDMappingClient

Specialized client for UniProt ID mapping operations.

::: bioetl.infrastructure.adapters.uniprot.idmapping_client.UniProtIDMappingClient
    options:
        show-root-heading: true
        show-source: false

### PubMedAdapter

Data source adapter for PubMed/NCBI E-utilities.

::: bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- ESearch/EFetch API integration
- Rate limiting (3 req/sec)
- XML response parsing

### CrossRefAdapter

Data source adapter for CrossRef metadata API.

::: bioetl.infrastructure.adapters.crossref.client.CrossRefAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Polite pool rate limiting
- DOI-based lookups
- Works endpoint integration

### OpenAlexAdapter

Data source adapter for OpenAlex scholarly data API.

::: bioetl.infrastructure.adapters.openalex.client.OpenAlexAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Rate limiting (10 req/sec)
- Cursor-based pagination
- Rich metadata extraction

### SemanticScholarAdapter

Data source adapter for Semantic Scholar API.

::: bioetl.infrastructure.adapters.semanticscholar.adapter.SemanticScholarAdapter
    options:
        show-root-heading: true
        show-source: false
        members:
            - --init--
            - fetch
            - health-check

**Features**:
- Rate limiting (100 req/5min)
- Paper and author endpoints
- Citation graph access

## Lock Adapters

### MemoryLock

In-memory lock implementation (Local-Only).

::: bioetl.infrastructure.locking.memory_lock.MemoryLock
    options:
        show-root-heading: true
        show-source: false
        members:
            - acquire
            - release
            - heartbeat

## Checkpoint Adapters

### LocalCheckpoint

Local filesystem checkpoint implementation.

::: bioetl.infrastructure.checkpoint.local_checkpoint.LocalCheckpoint
    options:
        show-root-heading: true
        show-source: false
        members:
            - save
            - load
            - delete

## Observability

Observability components are documented in [Observability](observability.md).

## Usage Example

```python
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate-limiter import TokenBucket

# Create rate limiter
limiter = TokenBucket(rate=5.0, capacity=10)

# Create client
client = UnifiedHTTPClient(
    rate-limiter=limiter,
    provider="chembl",
)

# Make request
response = await client.get("https://www.ebi.ac.uk/chembl/api/data/activity")
```

## See Also

- [Domain Ports](../domain/ports.md) - Interfaces implemented by adapters
