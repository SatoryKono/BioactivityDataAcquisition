# BioETL AI Rules — Unified

## Canonical Sources

This file is a condensed mirror, not a replacement for the canonical
governance stack.

- `AGENTS.md`
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

## Architecture (Clean / Ports & Adapters)

**Layers** (dependency direction: domain → application → infrastructure):
- **domain/**: Pure logic, Ports (typing.Protocol), NO I/O
- **application/**: Orchestration, use cases
- **infrastructure/**: Adapters, concrete implementations
- **composition/**: DI wiring, ONLY place knowing all layers
- **interfaces/**: CLI/adapters; may import domain/application/composition, but
  MUST NOT import concrete infrastructure implementations

**Import Matrix:**
| From ↓ To → | domain | app | infra | comp | iface |
|-------------|--------|-----|-------|--------|-------|
| domain      | ✅ | ❌ | ❌ | ❌ | ❌ |
| application | ✅ | ✅ | ❌ | ❌ | ❌ |
| infrastructure| ✅ | ❌ | ✅ | ❌ | ❌ |
| composition | ✅ | ✅ | ✅ | ✅ | ❌ |
| interfaces  | ✅ | ✅ | ❌ | ✅ | ✅ |

## Code Standards

**Every .py file MUST start with:**
```python
from __future__ import annotations
```

**Type hints:** `list[str]`, `X | None`, `X | Y`; public interfaces fully
annotated; `Any` only as a documented narrow boundary.
**Lint:** `mypy --strict`, `ruff`
**Coverage:** ≥85%

## Data Architecture (Medallion)

| Layer  | Format | Validation | Idempotency |
|--------|--------|------------|-------------|
| Bronze | JSONL+zstd | Minimal | Append-only |
| Silver | Delta Lake | Soft (drift) | Merge/Upsert |
| Gold   | Delta Lake | Strict | SCD Type 2 |

The exact final Silver/Gold DataFrame MUST pass Pandera validation immediately
before write; Gold validation is strict and fail-closed. Silver validation is soft
only for permissible schema drift; contract validation before write is mandatory
and must fail or quarantine invalid data.

**Gold Modes:** `overwrite` (aggregates), `append` (facts), `scd2` (history)
**VACUUM:** Weekly, 7 days retention
**Quarantine:** Single table, 30 days retention

## Critical Rules

1. **NO `random` in writers** — determinism required
2. **NO `datetime.now()` in infrastructure** — use `PipelineContext.started_at`
3. **JSON fields:** `Series[str]` with canonical JSON (NOT `Series[object]`)
4. **All adapters MUST have:** `async def health_check(self) -> HealthStatus`
5. **All services MUST have:** `async def aclose(self) -> None` (idempotent)
6. **Content Hash:** `sha256(provider + canonical_json(record)).hexdigest()`
7. **Secrets:** `BIOETL_{PROVIDER}_{KEY}` from env, NO hardcode
8. **PII in Silver:** Salted `sha256(lowercase(value) + SALT)`
9. **Artifacts:** stable/canonical/UTC output, write via tmp + `os.replace()`
10. **Technical debt:** budgets, thresholds and exclusions MUST NOT increase

## Testing

- **Unit:** Domain only, in-memory fakes
- **Integration:** VCR.py cassettes, sanitize secrets
- **E2E:** `@pytest.mark.e2e`, local-only
- **Architecture tests:** Layer boundaries, no random/datetime in wrong layers
- **Behavior changes:** regression tests required; assertions MUST NOT be
  weakened merely to pass the suite
- **Determinism:** control time/random/network with fixtures, seeds, mocks or VCR

## Adapter Pattern

```python
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class NewAdapter(BaseHttpAdapter):
    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort):
        super().__init__(http_client, logger)
        self.provider_name = "new-provider"
```

## Config Location

`configs/entities/{provider}/{entity}.yaml` — unified format (ADR-039)

## Verification Commands

```bash
uv run python -m scripts.engineering.qa check-exemptions
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q
uv run python -m pytest tests/architecture/test_regression_metrics.py -q
make test  # local suite with coverage
make lint  # ruff + mypy
```

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
