# Infrastructure Layer

Concrete implementations of domain ports.

## Purpose

Implements adapters for external systems: APIs, storage, locking, observability.

## Modules

### HTTP Adapters

| Module | Type | Diagram |
|--------|------|---------|
| `adapters/http/client.py` | adapter | [client.mmd](../../../docs/diagrams/infrastructure/adapters/http/client.mmd) |
| `adapters/http/circuit_breaker.py` | adapter | [circuit_breaker.mmd](../../../docs/diagrams/infrastructure/adapters/http/circuit_breaker.mmd) |
| `adapters/http/rate_limiter.py` | adapter | [rate_limiter.mmd](../../../docs/diagrams/infrastructure/adapters/http/rate_limiter.mmd) |
| `adapters/http/pagination.py` | adapter | - |

### Data Source Adapters

| Module | Type | Diagram |
|--------|------|---------|
| `adapters/chembl/client.py` | adapter | [chembl/client.mmd](../../../docs/diagrams/infrastructure/adapters/chembl/client.mmd) |
| `adapters/pubchem/client.py` | adapter | [pubchem/client.mmd](../../../docs/diagrams/infrastructure/adapters/pubchem/client.mmd) |
| `adapters/uniprot/client.py` | adapter | [uniprot/client.mmd](../../../docs/diagrams/infrastructure/adapters/uniprot/client.mmd) |

### Storage

| Module | Type | Diagram |
|--------|------|---------|
| `storage/bronze_writer.py` | adapter | [medallion.mmd](../../../docs/diagrams/infrastructure/storage/medallion.mmd) |
| `storage/delta_writer.py` | adapter | [medallion.mmd](../../../docs/diagrams/infrastructure/storage/medallion.mmd) |
| `storage/gold_writer.py` | adapter | [medallion.mmd](../../../docs/diagrams/infrastructure/storage/medallion.mmd) |
| `storage/s3_pool.py` | util | - |

### Locking

| Module | Type | Diagram |
|--------|------|---------|
| `locking/memory_lock.py` | adapter | [distributed_lock.mmd](../../../docs/diagrams/infrastructure/locking/distributed_lock.mmd) |
| `locking/redis_lock.py` | adapter | [distributed_lock.mmd](../../../docs/diagrams/infrastructure/locking/distributed_lock.mmd) |

### Checkpoint & Quarantine

| Module | Type | Diagram |
|--------|------|---------|
| `checkpoint/s3_checkpoint.py` | adapter | [s3_checkpoint.mmd](../../../docs/diagrams/infrastructure/checkpoint/s3_checkpoint.mmd) |
| `quarantine/unified_quarantine.py` | adapter | [unified_quarantine.mmd](../../../docs/diagrams/infrastructure/quarantine/unified_quarantine.mmd) |

### Observability

| Module | Type | Diagram |
|--------|------|---------|
| `observability/metrics.py` | adapter | [overview.mmd](../../../docs/diagrams/infrastructure/observability/overview.mmd) |
| `observability/prometheus_metrics.py` | adapter | [overview.mmd](../../../docs/diagrams/infrastructure/observability/overview.mmd) |
| `observability/noop_metrics.py` | adapter | [overview.mmd](../../../docs/diagrams/infrastructure/observability/overview.mmd) |
| `observability/lineage.py` | adapter | [overview.mmd](../../../docs/diagrams/infrastructure/observability/overview.mmd) |
| `observability/anomaly.py` | adapter | [overview.mmd](../../../docs/diagrams/infrastructure/observability/overview.mmd) |
| `observability/logging.py` | adapter | - |

### Factories & Config

| Module | Type | Diagram |
|--------|------|---------|
| `config.py` | config | - |
| `factories/storage.py` | factory | - |
| `factories/clients.py` | factory | - |

## Dependencies

- Uses: `domain` (ports, types, exceptions)
- Used by: `interfaces`

## Key Implementations

### Storage Adapters
- `BronzeWriter` - JSONL + zstd compression on S3
- `DeltaWriter` - Delta Lake merge/upsert for Silver
- `GoldWriter` - Pandera-validated Delta/Parquet for Gold

### Locking
- `MemoryLock` - For local development
- `RedisDistributedLock` - Production with Lua scripts

### HTTP Client
`UnifiedHTTPClient` combines:
- Rate limiting (TokenBucket)
- Circuit breaker (CLOSED→OPEN→HALF_OPEN)
- Retry with exponential backoff
