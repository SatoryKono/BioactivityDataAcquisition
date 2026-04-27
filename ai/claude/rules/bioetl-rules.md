# BioETL Project Rules for Claude

> Canonical source: `docs/00-project/RULES.md` (v6.1.2)

## 1. Architecture (Clean Architecture / Ports & Adapters)

**Core Philosophy**: "Pragmatic engineering" — avoid over-engineering, accelerate time-to-market.

**Layer Structure** (`src/bioetl/`):
```
domain/          # Pure business logic, Protocols (typing.Protocol), NO I/O
application/     # Orchestration, use cases, pipeline definitions
infrastructure/  # Adapters: HTTP, DB, filesystem implementations
composition/     # DI wiring, bootstrap, factories — ONLY place knowing ALL layers
interfaces/      # CLI, API handlers — may import from all layers
```

**Critical Import Rules** (enforced by `import-linter`):
- `domain/` → can import: domain only
- `application/` → can import: domain, application
- `infrastructure/` → can import: domain, infrastructure
- `composition/` → can import: domain, application, infrastructure, composition
- `interfaces/` → can import: all layers (including infrastructure directly for health checks)

**Ports & Protocols**:
- Define in `domain/ports/` via `typing.Protocol`
- Critical ports MUST be `@runtime_checkable`: DataSourcePort, FilterableDataSourcePort, HealthCheckPort, StoragePort
- Import from facade: `from bioetl.domain.ports import ...`
- `*Port` suffix = cross-layer contract in `domain/ports/`
- `*Protocol` suffix = layer-internal structural typing (allowed outside domain/ports/)

**Health Check Protocol** (ALL adapters MUST implement):
```python
from bioetl.domain.types import HealthStatus

async def health_check(self) -> HealthStatus:
    """Returns: HEALTHY, DEGRADED, or UNHEALTHY
    MUST be async, MUST NOT raise exceptions, SHOULD cache 30 sec"""
```

**Resource Cleanup** (ALL adapters/services MUST implement):
```python
async def aclose(self) -> None:
    """Idempotent cleanup, MUST NOT raise, SHOULD nullify: self._client = None"""
```

## 2. Code Standards

**Every Python file MUST start with:**
```python
from __future__ import annotations  # After docstring if present
```

**Type Hints** (modern style only):
- `list[str]` not `List[str]`
- `X | None` not `Optional[X]`
- `X | Y` not `Union[X, Y]`

**Quality Gates**:
- `mypy --strict` — type checking
- `ruff` — linting and formatting
- `pytest --cov-fail-under=85` — coverage requirement

## 3. Data Architecture (Medallion)

| Layer  | Format        | Validation               | Retention                 | Idempotency                        |
|--------|---------------|--------------------------|---------------------------|------------------------------------|
| Bronze | JSONL + zstd  | Minimal                  | 90 days hot → archive     | Append-only, path-based            |
| Silver | Delta Lake    | Soft (schema drift)      | Permanent                 | Merge/Upsert, ACID required        |
| Gold   | Delta Lake    | Strict (`strict=True`)   | Permanent                 | SCD Type 2 or date partitioning    |

**Silver Write Modes** (`SilverWriteMode` enum):
- `MERGE` — Upsert by primary keys (default incremental)
- `APPEND` — Insert without dedup
- `DELETE` — Full rewrite (not OVERWRITE)

**Gold Write Modes** (`GoldWriteMode` enum):
- `OVERWRITE` — Recomputed aggregates
- `APPEND` — Fact streams without retro-fixes
- `SCD2` — Slowly Changing Dimensions Type 2 (history)

**SCD2 Configuration** (REQUIRED for reference data):
```yaml
sink:
  gold:
    mode: scd2
    scd_config:
      valid_from_col: _valid_from
      valid_to_col: _valid_to
      current_flag_col: _is_current
      version_col: _version
```

**Delta Lake Maintenance**:
- Engine: `delta-rs` (Rust core)
- **VACUUM MUST run weekly** with `retention-period=7 days`
- Forensic retention: default 7 days, max 30 days for critical

**Quarantine** (Unified table `common.quarantine`):
- 30 days retention, dq-status workflow: NEW → UNDER-REVIEW → IGNORED/REPROCESSED/EXPIRED
- **Sentinel values (-1, "N/A", 9999) are FORBIDDEN**
- Payload truncated to 64KB

## 4. Critical Implementation Rules

1. **Determinism** — NO `random` module in storage writers
2. **Timestamp Source** — NO `datetime.now()` in infrastructure; use `PipelineContext.started_at`
3. **JSON Fields** — Store as canonical JSON strings (`Series[str]`), NOT native list/object (`Series[object]`)
4. **Health Checks** — ALL adapters MUST implement `async def health_check(self) -> HealthStatus`
5. **Cleanup** — ALL services MUST implement `async def aclose(self) -> None` (idempotent)
6. **Content Hash** — `sha256(provider + canonical_json(normalized_record)).hexdigest()`
   - Floats: `round(val, 10)`, NaN/Inf → null, Dates: ISO format, Strings: strip()
   - Exclude `_` prefixed meta-fields from hash
7. **Secrets** — Format: `BIOETL_{PROVIDER}_{KEY}` from env vars, NO hardcoding
8. **PII in Silver** — Salted hash: `sha256(lowercase(value) + SALT)`

## 5. Testing Strategy

| Test Type    | Scope                             | Key Requirements                          |
|--------------|-----------------------------------|-------------------------------------------|
| Unit         | Domain logic only                 | In-memory fakes, NO MagicMock preferred   |
| Integration  | API adapters                      | VCR.py cassettes, sanitize secrets in CI  |
| E2E          | Full pipeline cycle               | `@pytest.mark.e2e`, local-only runtime    |
| Architecture | Layer boundaries                  | NO random in writers, NO datetime in infra|
| Contract     | Live API validation               | Monthly runs, separate CI workflow        |

**Coverage**: ≥85% line coverage enforced in CI.

**Architecture Test Files** (critical):
- `test_no_random_in_writers.py`
- `test_no_datetime_now_in_infrastructure.py`
- `test_no_structlog_in_application_interfaces.py`
- `test_future_annotations_policy.py`
- `test_quality_debt_scorecard.py`

## 6. Creating New Adapter

**HTTP Adapter** (preferred):
```python
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class NewProviderAdapter(BaseHttpAdapter):
    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort):
        super().__init__(http_client, logger)
        self.provider_name = "new-provider"
```

**Sync Adapter** (for legacy libraries):
```python
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

class LegacyAdapter(BaseSyncAdapter):
    provider_name = "legacy"

    def __init__(self, logger: LoggerPort, rate_limiter: TokenBucket,
                 circuit_breaker: CircuitBreaker, thread_pool: ThreadPoolExecutor):
        super().__init__(logger, rate_limiter, circuit_breaker, thread_pool)
```

**UnifiedHTTPClient includes**: TokenBucket (rate limiting), Circuit Breaker, Retry with exponential backoff, Metrics integration.

## 7. Configuration

**Unified Entity Config** (ADR-039): `configs/entities/{provider}/{entity}.yaml`

Combines: pipeline, schema, quality rules, filters, contracts, hash-policy.

## 8. Developer Commands

```bash
# Setup
make install          # venv + deps
make setup-plugins    # pytest/pre-commit

# Development
make test             # stable suite with coverage (no E2E)
make lint             # ruff + mypy
make run-local        # sample pipeline (chembl_activity, limit=10)

# Architecture verification
uv run python -m scripts.engineering.qa check-exemptions
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q
uv run python -m pytest tests/architecture/test_regression_metrics.py -q

# E2E
pytest tests/e2e/ -v -m e2e
```

## 9. When Generating Code

**ALWAYS verify**:
1. Correct layer for new code (check import matrix)
2. `from __future__ import annotations` at top
3. Modern type hints only
4. Health check and aclose methods for adapters
5. No random/datetime violations in wrong layers
6. JSON fields as Series[str] with canonical serialization
7. Proper Delta Lake write modes (no OVERWRITE in Silver)
8. Test coverage ≥85%

**When refactoring**: Track debt outcome — improved/unchanged/worsened with justification.
