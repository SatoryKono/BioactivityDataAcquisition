# Extending BioETL
*Синхронизировано с RULES.md v5.0 (2025-12-15)*

This guide provides step-by-step recipes for adding new providers, pipelines, and services without modifying core code.

## Уровни Требований (RFC 2119)
- **MUST**: Абсолютное требование.
- **SHOULD**: Сильная рекомендация.
- **MAY**: На усмотрение разработчика.

## 1. Adding a new provider via configs and registries

### 1.1. Define the ABC (MUST)

Location: `src/bioetl/domain/clients/<provider>/contracts.py`

Use the three-layer pattern demonstrated by `DataClientABC`:

```python
from typing import Protocol, Iterator
from bioetl.domain.models import Query, RawRecord

class DataSourcePort(Protocol):
    """Port for data source interactions."""
    
    def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    def health_check(self) -> bool: ...
```

### 1.2. Create a default factory (MUST)

Location: `src/bioetl/infrastructure/clients/<provider>/factories.py`

Expose `default_<provider>_<entity>()`:

```python
def default_chembl_activity() -> ChemblActivityClientImpl:
    """Factory for ChEMBL activity client with default configuration."""
    return ChemblActivityClientImpl(
        base_url=os.environ.get("BIOETL_CHEMBL_BASE_URL", "https://www.ebi.ac.uk"),
        timeout=30,
        rate_limit=RateLimitConfig(requests_per_second=5, burst=10),
    )
```

### 1.3. Implement the client (MUST)

Location: `src/bioetl/infrastructure/clients/<provider>/impl/`

Classes **MUST** be suffixed `Impl`:

```python
class ChemblActivityClientHTTPImpl(DataSourcePort):
    """HTTP implementation of ChEMBL activity client."""
    
    def fetch(self, query: Query) -> Iterator[RawRecord]:
        # Implementation with retry, circuit breaker, rate limiting
        ...
    
    def health_check(self) -> bool:
        # GET /chembl/api/data/status.json
        ...
```

### 1.4. Register in YAML (MUST)

**ABC Registry** (`src/bioetl/infrastructure/clients/base/abc_registry.yaml`):
```yaml
chembl_activity:
  abc: bioetl.domain.clients.chembl.contracts.ChemblActivityProtocol
  default: bioetl.infrastructure.clients.chembl.factories.default_chembl_activity
```

**Impl Mapping** (`src/bioetl/infrastructure/clients/base/abc_impls.yaml`):
```yaml
chembl_activity:
  http: bioetl.infrastructure.clients.chembl.impl.ChemblActivityClientHTTPImpl
  mock: bioetl.infrastructure.clients.chembl.impl.ChemblActivityClientMockImpl
```

Keys **MUST** be in `lower_snake_case`.

### 1.5. Expose in provider registry (MUST)

Location: `src/bioetl/infrastructure/config/provider_registry.py`

Register for DI container resolution from configs.

## 2. Wiring pipeline configs

### 2.1. Provider-level config (SHOULD)

Location: `configs/providers/<provider>.yaml`

```yaml
# configs/providers/chembl.yaml
chembl:
  base_url: https://www.ebi.ac.uk
  rate_limit:
    requests_per_second: 5
    burst: 10
  health_check:
    endpoint: /chembl/api/data/status.json
    timeout: 5
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
```

### 2.2. Pipeline config (MUST)

Location: `configs/pipelines/<provider>/<entity>.yaml`

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline:
  name: activity_chembl
  provider: chembl
  entity: activity

source:
  type: api
  load_strategy: incremental
  watermark_field: updated_at

transform:
  version: "1.0.0"
  steps:
    - normalize_units
    - validate_smiles
    - deduplicate

sink:
  silver:
    path: s3://bioetl/silver/chembl/activity/
    format: delta
    mode: merge
    primary_key: [id]
    partition_by: [year, month]
    classification: public
    forensic_retention: false

  gold:
    path: s3://bioetl/gold/chembl/activity_aggregated/
    format: delta
    mode: overwrite

dq_rules:
  soft_fail_threshold: 0.05
  hard_fail_threshold: 0.20

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 300

rate_limit:
  requests_per_second: 5
  burst: 10

backfill:
  lock_timeout: 300
  wait_for_lock: false
```

### 2.3. Pipeline modules (MUST)

Location: `src/bioetl/pipelines/<provider>/<entity>/`

Stage names **MUST** follow the sequence:
- `extract.py`
- `transform.py`
- `validate.py`
- `export.py` (or `write.py`)

### 2.4. Pipeline documentation (MUST)

Location: `docs/application/pipelines/<provider>/<entity>/`

Naming: `NN-<entity>-<provider>-<topic>.md`

Example:
- `01-activity-chembl-overview.md`
- `02-activity-chembl-schema.md`
- `03-activity-chembl-transform.md`

## 3. Health Check Integration (MUST)

Every new provider **MUST** implement health check:

| Провайдер | Endpoint | Timeout |
|-----------|----------|---------|
| ChEMBL | `GET /chembl/api/data/status.json` | 5s |
| PubChem | `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` | 5s |
| UniProt | `GET /rest/beta/health` | 5s |
| Others | Generic Probe (lightweight GET) | 5s |

**Provider Health States**:
| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors за 5 мин | Normal |
| Degraded | 1-2 consecutive errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors | Pause, Alert P2 |

## 4. Creating new services or hooks

### 4.1. Reusable services (SHOULD)

Location: `src/bioetl/infrastructure/<adapter_folder>/`

Examples:
- `observability/`
- `logging/`
- `transform/`

Module names: `snake_case`. Classes: `PascalCase`.

### 4.2. Middleware and hooks (MAY)

Location: `src/bioetl/infrastructure/clients/base/middleware.py`

Or provider-specific: `src/bioetl/infrastructure/clients/<provider>/middleware.py`

```python
class RateLimitMiddleware:
    """Middleware for rate limiting API requests."""
    
    def __init__(self, token_bucket: TokenBucket):
        self._bucket = token_bucket
    
    async def __call__(self, request: Request) -> Response:
        await self._bucket.acquire()
        return await request.send()
```

### 4.3. Export public symbols (SHOULD)

Use `__all__` for container-resolvable exports without editing core modules.

## 5. Leveraging DI and container factories

### 5.1. YAML registries (MUST)

Bind implementations through `abc_registry.yaml` and `abc_impls.yaml`. DI loader reads these at runtime.

### 5.2. Provider factories (SHOULD)

Inject via configuration:

```python
# src/bioetl/infrastructure/clients/chembl/factories.py
def create_chembl_client(config: ChemblConfig) -> ChemblClientImpl:
    return ChemblClientImpl(
        request_builder=ChemblRequestBuilder(config.base_url),
        paginator=ChemblPaginator(config.page_size),
        response_parser=ChemblResponseParser(),
        rate_limiter=TokenBucket(config.rate_limit),
        circuit_breaker=CircuitBreaker(config.circuit_breaker),
    )
```

### 5.3. Deterministic configs (MUST)

| Requirement | Example |
|-------------|---------|
| Timeouts | `timeout: 30` |
| Retries | `max_attempts: 3` |
| Ordering | `sort_keys: true` |
| Secrets | `${BIOETL_CHEMBL_API_KEY}` |

Secrets **MUST NOT** be hardcoded. Only env references.

## 6. Schema Registration (MUST)

### 6.1. Pandera Schema

Location: `src/bioetl/domain/schemas/<provider>/<entity>.py`

```python
import pandera as pa
from pandera.typing import Series

class ActivitySchema(pa.DataFrameModel):
    """Schema for ChEMBL activity data."""
    
    id: Series[str] = pa.Field(nullable=False)
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=True)
    standard_value: Series[float] = pa.Field(nullable=True, ge=0)
    standard_units: Series[str] = pa.Field(nullable=True)
    
    class Config:
        strict = True
        ordered = True
```

### 6.2. Data Contract (MUST for Gold)

Location: `docs/contracts/gold/<entity>.json`

Versioning: `{entity}_v{major}.{minor}`

## 7. Quarantine Integration (MUST)

All pipelines **MUST** route DQ failures to `common.quarantine`:

```python
async def handle_dq_error(
    record: RawRecord,
    error: ValidationError,
    batch_id: UUID,
) -> None:
    await quarantine_writer.write(
        QuarantineRecord(
            ingestion_ts=datetime.utcnow(),
            pipeline=f"{provider}_{entity}",
            error_code=error.code,
            payload=record.to_json()[:64*1024],  # Truncate to 64KB
            payload_hash=hash_record(record),
            bronze_batch_id=batch_id,
            dq_status=DQStatus.NEW,
        )
    )
```

## 8. Backfill Lock Integration (MUST for Backfill)

```python
async def acquire_backfill_lock(
    provider: str,
    entity: str,
    run_type: str,
    run_id: UUID,
    timeout: int = 300,
) -> Lock:
    key = f"lock:{provider}_{entity}"
    if run_type in ("backfill", "rebuild"):
        key += ":exclusive"
    
    return await redis.acquire_lock(
        key=key,
        owner_id=str(run_id),
        ttl=60,
        heartbeat_interval=20,
        max_duration=4 * 3600,
        wait_timeout=timeout if wait_for_lock else 0,
    )
```

## Compliance Checklist

Before submitting a new provider/pipeline:

- [ ] ABC defined in `domain/clients/`
- [ ] Factory in `infrastructure/clients/<provider>/factories.py`
- [ ] Impl in `infrastructure/clients/<provider>/impl/`
- [ ] Registered in `abc_registry.yaml` and `abc_impls.yaml`
- [ ] Pipeline config in `configs/pipelines/<provider>/<entity>.yaml`
- [ ] Pipeline modules: `extract.py`, `transform.py`, `validate.py`, `export.py`
- [ ] Pandera schema in `domain/schemas/`
- [ ] Gold Data Contract in `docs/contracts/gold/`
- [ ] Health check endpoint configured
- [ ] Circuit breaker parameters set
- [ ] Rate limiting implemented
- [ ] Quarantine integration tested
- [ ] Backfill lock mechanism (if applicable)
- [ ] Documentation in `docs/application/pipelines/`
- [ ] Tests: Unit, Integration (VCR.py), Golden
- [ ] Coverage ≥85%
