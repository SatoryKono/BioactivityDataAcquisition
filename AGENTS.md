# BioETL Project Instructions

## Project Overview

BioETL is a Python ETL pipeline for bioactivity data acquisition from multiple providers (ChEMBL, PubChem, PubMed, Semantic Scholar, CrossRef, OpenAlex, UniProt). Uses Hexagonal Architecture with Medallion data layers (Bronze → Silver → Gold).

## Tech Stack

- **Python 3.11+** (**3.13 recommended**), **uv** for dependency management
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
  providers/     — Provider YAML configs (chembl.yaml, pubmed.yaml, etc.)
  entities/      — Unified entity pipeline configs ({provider}/{entity}.yaml)
  composites/    — Composite pipeline configs ({entity}.yaml)
tests/
  unit/          — Unit tests mirroring src/ structure
  integration/   — Integration tests
  e2e/           — End-to-end with VCR cassettes
  architecture/  — Import boundary tests
  fixtures/vcr/  — VCR cassettes per provider
```

## Evidence Anchors

Before proposing repo-wide refactors, package moves, or topology claims, consult the current evidence baseline:

- File structure baseline: [docs/reports/evidence/project-file-structure/SUMMARY.md](docs/reports/evidence/project-file-structure/SUMMARY.md)
- File structure decision summary: [docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md](docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md)
- Package topology baseline: [docs/reports/evidence/project-package-topology/SUMMARY.md](docs/reports/evidence/project-package-topology/SUMMARY.md)
- Package topology synthesis: [docs/reports/evidence/project-package-topology/03-synthesis/SYN-project-package-topology.md](docs/reports/evidence/project-package-topology/03-synthesis/SYN-project-package-topology.md)
- Topology vs governance cross-synthesis: [docs/reports/evidence/project-package-topology/03-synthesis/CROSS-SYNTHESIS-topology-vs-governance-signals.md](docs/reports/evidence/project-package-topology/03-synthesis/CROSS-SYNTHESIS-topology-vs-governance-signals.md)
- Package topology decisions: [docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md](docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md)
- Governance signals baseline: [docs/reports/evidence/governance-signals/SUMMARY.md](docs/reports/evidence/governance-signals/SUMMARY.md)
- Governance signals decisions: [docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md](docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md)

Use these evidence packs as the default calibration layer:
- Package count alone is not a refactor trigger.
- Family-level topology is a better hotspot unit than whole-layer breadth.
- Governance signals decide where to act; topology mostly decides where to look.

## Common Commands

```bash
uv run python -m pytest tests/ -x -q              # Run all tests
uv run python -m pytest tests/architecture/ -v     # Architecture boundary tests
uv run python -m mypy --strict src/bioetl/         # Type checking
uv run python -m bioetl run --pipeline chembl_molecule --limit 100  # Run pipeline
```

## Dashboard Extension Guide (LLM)

If the task touches `grafana/dashboards/*.json`, dashboard navigation, or
Loki/Tempo drilldown behavior, read:

- `docs/03-guides/dashboards/dashboard-extension-llm.md`

 rj### Unified script entry points and developer workflow (project-specific)

- All repository helper scripts are available as python modules under `scripts/` and can be run as `python -m scripts.<group> <command>` (examples below). Prefer `uv run python -m scripts.<group> <command>` when `uv` is available.
- Common script groups present in the repo: `scripts.qa`, `scripts.docs`, `scripts.schema`, `scripts.diagrams`, `scripts.data`, `scripts.repo`, `scripts.ops`, `scripts.dev`, `scripts.diagnostics` (see the `scripts/` directory for exact commands and `--help`).
- Canonical examples used in CI and docs (copy/paste):

```bash
# Documentation checks
uv run python -m scripts.docs check-links --links --specs --configs
uv run python -m scripts.docs check-drift --ports --classes
uv run python -m scripts.docs check-docstrings --summary

# Schema/config validation
uv run python -m scripts.schema validate-configs
uv run python -m scripts.schema check-invariants

# Dev / type-check
uv sync --extra dev --extra tests --extra tracing    # sync dev deps (preferred)
uv run python -m mypy --strict src/bioetl/            # type checks (or use .venv)
```

- Dev environment note (Windows/.venv fallback): many scripts use the pattern `.venv/Scripts/python.exe -m ...` when `uv` is not present. See `scripts/dev/run_mypy.ps1` for the exact fallback logic.
- CI note: GitHub Actions uses the repository-local `.github/actions/setup-python-uv` action and runs `uv run` for many gates; follow the same `uv`-first approach locally to reproduce CI behavior (see `.github/workflows/tests.yml`).

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
