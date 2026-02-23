# Memory: py-code-bot

*Version: 1.0.0 | Date: 2026-02-23 | Parent: agent-memory.md*

> **Focus**: Production code implementation, scaffolding, transformers, adapters, schemas, Ports/Protocols.

---

## 1. Identity & Scope

- **Role**: Production code writer — implements RF-* from plan
- **Write zone**: `src/bioetl/`, `tests/`
- **Output artifacts**: `04-refactoring-log.md`
- **ID system**: Uses RF-* from py-plan-bot
- **Model**: opus
- **Note**: NOT registered as subagent_type — code is written directly by main agent

---

## 2. Layer Architecture & Constraints

### Directory Structure

```
src/bioetl/
├── domain/          # Pure logic, Protocols (Ports). NO I/O.
│   ├── entities/    # Pydantic entities (frozen value objects)
│   ├── ports/       # Protocol definitions (*Port)
│   ├── types/       # Shared type definitions
│   ├── exceptions/  # Shared exceptions
│   ├── config/      # Configuration value objects
│   └── policies/    # Domain policies
├── application/     # Pipelines, Use Cases, orchestration
│   ├── pipelines/   # Pipeline runners, transformers
│   └── services/    # Application services
├── composition/     # Composition Root
│   ├── bootstrap/   # DI assembly
│   └── factories/   # Factory pattern with @register
├── infrastructure/  # Adapters (HTTP, storage)
│   ├── adapters/    # API clients per provider
│   ├── schemas/     # Pandera validation schemas
│   ├── storage/     # Bronze/Silver/Gold writers
│   └── observability/ # Logging, metrics
└── interfaces/      # CLI
    └── cli/         # Click commands
```

### Import Rules (MUST)

| Layer | Can Import From |
|-------|----------------|
| domain | domain only |
| application | domain, application |
| infrastructure | domain, infrastructure |
| composition | all except interfaces |
| interfaces | all |

### Code Style (MUST)

```python
from __future__ import annotations  # MUST in all files

# MUST: type hints on all public API
def transform(self, record: dict[str, Any]) -> TransformedRecord: ...

# MUST: DI via constructor
class MyService:
    def __init__(self, client: ClientPort, logger: LoggerPort | None = None):
        self._client = client
        self._logger = logger or NoOpLogger()

# MUST: structured logging
self._logger.info("records_transformed", count=len(results), pipeline=self._name)

# MUST NOT: print(), sentinel values, hardcoded credentials
```

---

## 3. Implementation Patterns

### A. Transformer

```python
class {Provider}{Entity}Transformer:
    def __init__(
        self,
        logger: LoggerPort | None = None,
    ) -> None:
        self._logger = logger or NoOpLogger()

    def transform(self, raw_records: list[dict[str, Any]]) -> list[{Entity}]:
        results: list[{Entity}] = []
        for record in raw_records:
            try:
                entity = self._transform_single(record)
                results.append(entity)
            except Exception as exc:
                self._logger.warning("transform_record_failed", error=str(exc))
        return results
```

### B. API Client

```python
class {Provider}{Entity}Client:
    def __init__(
        self,
        http_client: HTTPClientPort,
        base_url: str,
        logger: LoggerPort | None = None,
    ) -> None:
        self._http = http_client
        self._base_url = base_url
        self._logger = logger or NoOpLogger()

    async def health_check(self) -> HealthStatus:
        """MUST be async, MUST return HealthStatus."""
        ...
```

### C. Pydantic Entity

```python
class {Entity}(BaseModel):
    {primary_key}: str = Field(..., description="Business key")
    content_hash: str = Field(..., description="SHA-256 version hash")
    model_config = {"frozen": True}  # Immutable value object
```

### D. Pandera Schema

```python
class {Entity}SilverSchema(pa.DataFrameModel):
    {primary_key}: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    class Config:
        strict = "filter"
        coerce = True
```

### E. Port/Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class DataSourcePort(Protocol):
    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...
```

---

## 4. Scaffolding Checklist (New Entity)

All 10 files MUST be generated:

```
src/bioetl/
├── domain/entities/{provider}_{entity}.py          # Pydantic entity
├── application/pipelines/{provider}/{entity}_transformer.py  # Transformer
├── infrastructure/
│   ├── adapters/{provider}/client.py      # API client (or update existing)
│   └── schemas/{provider}/{entity}_schema.py       # Pandera schemas
├── composition/factories/                          # Update registry
configs/
├── pipelines/{provider}/{entity}.yaml              # Pipeline config
├── dq/entities/{provider}/{entity}.yaml            # DQ rules
└── filter/entities/{provider}/{entity}.yaml        # Filter rules
tests/
├── unit/application/pipelines/{provider}/test_{entity}_transformer.py
├── unit/infrastructure/schemas/{provider}/test_{entity}_schema.py
└── integration/{provider}/test_{entity}_pipeline.py
```

---

## 5. Medallion Architecture

| Layer | Format | Key Rules |
|-------|--------|-----------|
| Bronze | JSONL + zstd | Append-only, 90d retention |
| Silver | Delta Lake | merge/upsert by `content_hash`, ACID mandatory, NO raw Parquet |
| Gold | Delta/Parquet | SCD Type 2 or date partitions |

- **Content Hash**: `sha256(provider + canonical_json(record))`
- **DQ Thresholds**: soft=5%, hard=20%

---

## 6. Pre/Post Implementation Checks

### Before RF-*

```bash
wc -l src/bioetl/path/to/file.py
grep "^from\|^import" src/bioetl/path/to/file.py
find tests/ -name "test_*.py" -exec grep -l "ClassName" {} \;
```

### After RF-*

```bash
# Type checking
mypy src/bioetl/path/to/file.py --strict

# Import boundaries
grep "^from\|^import" src/bioetl/path/to/file.py | \
  grep -v "domain\.\|typing\|__future__\|pydantic\|pandera"

# Forbidden patterns
grep -n "print(\|= -1\|= \"N/A\"\|sentinel" src/bioetl/path/to/file.py

# Architecture tests
pytest tests/architecture/ -v --tb=short -q
```

---

## 7. Naming Conventions

### Classes

| Type | Suffix |
|------|--------|
| Factory | `*Factory` |
| Client | `*Client` |
| Port | `*Port` |
| Service | `*Service` |
| Transformer | `*Transformer` |
| Error | `*Error` |
| Schema | `*Schema` |
| Config | `*Config` |

### Functions

| Prefix | Use |
|--------|-----|
| `get_*` | Local data |
| `fetch_*` | Network/I/O |
| `iter_*` | Generators |
| `create_*` / `build_*` | Creation |
| `validate_*` | Validation |
| `is_*` / `has_*` / `can_*` | Boolean |

### Modules

- snake_case, no abbreviations, descriptive, single responsibility
- Good: `delta_writer.py`, `bronze_writer.py`
- Bad: `dw.py`, `utils.py`, `helpers.py`

---

## 8. Integration with Other Agents

| Event | Action |
|-------|--------|
| Plan ready (py-plan-bot) | -> Implement RF-* |
| RF-* implemented | -> py-test-bot (final) + py-config-bot (if config) |
| mypy/architecture fail | -> py-debug-bot |
| Need additional RF-* | -> py-plan-bot (update plan) |
| New entity scaffolding | -> py-config-bot (3 configs) |
| Code complete | -> py-doc-bot (docstrings) -> py-audit-bot (final) |

---

## 9. Key Files for Implementation

| What | Path |
|------|------|
| Domain Ports | `src/bioetl/domain/ports/` |
| Domain Entities | `src/bioetl/domain/entities/` |
| Transformers | `src/bioetl/application/pipelines/` |
| Adapters | `src/bioetl/infrastructure/adapters/{provider}/` |
| Schemas | `src/bioetl/infrastructure/schemas/{provider}/` |
| Factories | `src/bioetl/composition/factories/` |
| Bootstrap | `src/bioetl/composition/bootstrap/` |

---

*This memory file is specific to py-code-bot. For general project context see `agent-memory.md`.*
