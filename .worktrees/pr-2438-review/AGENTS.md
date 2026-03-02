# BioETL Project Instructions

## Project Overview

BioETL is a Python ETL pipeline for bioactivity data acquisition from multiple providers (ChEMBL, PubChem, PubMed, Semantic Scholar, CrossRef, OpenAlex, UniProt). Uses Hexagonal Architecture with Medallion data layers (Bronze → Silver → Gold).

## Tech Stack

- **Python 3.13**, **uv** for dependency management
- **Pandera** for DataFrame schema validation
- **Delta Lake** for Silver layer (MUST, no raw Parquet)
- **httpx** for async HTTP, **structlog** for logging
- **pytest** + **VCR.py** for testing, **mypy --strict** for types
- Run commands via `uv run python -m pytest ...` or `uv run python -m bioetl ...`

## Architecture Rules (CRITICAL)

### Import Matrix — NEVER violate:

| From \ To     | domain | application | infrastructure | composition | interfaces |
|---------------|--------|-------------|----------------|-------------|------------|
| domain        | OK     | NO          | NO             | NO          | NO         |
| application   | OK     | OK          | NO             | NO          | NO         |
| infrastructure| OK     | NO          | OK             | NO          | NO         |
| composition   | OK     | OK          | OK             | OK          | NO         |
| interfaces    | OK     | OK          | OK             | OK          | OK         |

- Infrastructure CAN import any domain modules (ports, types, exceptions, entities, config).
- Ports MUST be imported from `bioetl.domain.ports` facade, NOT internal modules.
- Domain layer MUST NOT contain I/O (no requests, httpx, open(), structlog).

### Dependency Injection

- MUST inject dependencies via constructor, NOT hard-code them.
- MUST NOT use Service Locator pattern.
- Factory calls MUST only be in `composition/` layer.
- NO module-level side effects in application/domain.

### Naming Conventions

- Classes: use proper suffixes — `*Port`, `*Service`, `*Factory`, `*Client`, `*Adapter`, `*Transformer`, `*Schema`, `*Config`, `*Error`.
- Functions: `get_*` (local), `fetch_*` (I/O), `iter_*` (generators), `create_*`/`build_*` (construction), `validate_*`, `is_*`/`has_*`/`can_*` (boolean).
- Private attributes: single underscore `self._field`.
- Constants: `UPPER_SNAKE_CASE`. Enums: `UPPER_SNAKE_CASE` members.

### Type Annotations

- All public functions MUST have type annotations.
- Code MUST pass `mypy --strict`.
- Avoid bare `Any` without justification comment.

## Key Directories

```
src/bioetl/
  domain/        — Pure business logic, ports (Protocol), types, exceptions
  application/   — Use cases, orchestration, transformers
  infrastructure/— Adapters (HTTP clients), storage, config
  composition/   — DI wiring, factories, bootstrap
  interfaces/    — CLI (Click)
configs/
  sources/       — Provider YAML configs (chembl.yaml, pubmed.yaml, etc.)
  pipelines/     — Pipeline and composite pipeline configs
tests/
  unit/          — Unit tests mirroring src/ structure
  integration/   — Integration tests
  e2e/           — End-to-end with VCR cassettes
  architecture/  — Import boundary tests
  fixtures/vcr/  — VCR cassettes per provider
```

## Common Commands

```bash
uv run python -m pytest tests/ -x -q              # Run all tests
uv run python -m pytest tests/architecture/ -v     # Architecture boundary tests
uv run python -m mypy --strict src/bioetl/         # Type checking
uv run python -m bioetl run --pipeline chembl_molecule --limit 100  # Run pipeline
```

## What NOT to Do

- NEVER import from infrastructure in domain or application layers.
- NEVER use raw Parquet for Silver layer (use Delta Lake).
- NEVER hard-code secrets or credentials.
- NEVER use `print()` — use structured logging via LoggerPort.
- NEVER use blocking I/O in async functions.
- NEVER create concrete dependencies inside classes (use DI).
- NEVER commit .env files with real API keys.

## Exceptions — NOT Violations

- `TYPE_CHECKING` imports across layers are OK.
- Optional params with defaults (`policy: Policy | None = None`) are OK.
- Null Object pattern (`NoOpTracing`) is OK.
- Config dataclasses with defaults are OK.
- Infrastructure importing domain types/ports/exceptions is OK by design.
