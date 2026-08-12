# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen)](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/workflows/tests.yml)
[![Version](https://img.shields.io/badge/version-6.1.0-blue)](CHANGELOG.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](.github/SECURITY.md)

> **Canonical repository:** [SatoryKono/BioactivityDataAcquisition](https://github.com/SatoryKono/BioactivityDataAcquisition)

**BioETL** is a robust, scalable data engineering framework designed to acquire, normalize, and process bioactivity data
from major public repositories (ChEMBL, PubChem, UniProt, etc.) into a unified, analysis-ready **Delta Lake** warehouse.

______________________________________________________________________

## Key Features

- **Medallion Architecture**: Structured data flow (Bronze -> Silver -> Gold) ensuring data quality and traceability.
- **Delta Lake Core**: ACID transactions, schema enforcement, and time travel capabilities.
- **Resilience**: Built-in circuit breakers, exponential backoff retries, and immutable Quarantine for rejected records.
- **Local-First Design**: In-memory locking, local file storage -- no external services required ([ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md)).
- **Deterministic Writes**: Reproducible outputs and deterministic retries ([ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md)).
- **Run Control Plane**: Immutable run manifests and append-only ledgers for provenance, replay analysis, and artifact linkage ([ADR-044](docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)).
- **Observability by Design**: Metrics, tracing, and logging ports ([ADR-017](docs/02-architecture/decisions/ADR-017-observability-architecture.md)).
- **Unified Entity Configuration**: All **22** standard provider/entity pipeline configs under `configs/entities/{provider}/{entity}.yaml`, plus composite configs under `configs/entities/composite/` ([ADR-039](docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md)).
- **Monitoring Surface Reduction**: Opt-in monitoring stack (Prometheus/Pushgateway/Grafana/renderer) with Loki/Tempo/Quarantine Explorer removed from default shipping (2026-07-23).
- **Operator Dashboards**: Unified L0/L1 Grafana default window `time.from=now-12h` (`time.to=now`, `refresh=30s`) including `bioetl-control-plane-v1`; record-level quarantine forensics via CLI `bioetl quarantine inspect`.
- **KPI Ownership Contract**: Canonical/mirror KPI ownership is machine-readable in `docs/03-guides/dashboards/contracts/navigation-links.yaml` (`kpi_ownership`), with integration tests enforcing mirror fallback links `Open canonical KPI view`.
- **Unified HTTP Client**: Standardized rate limiting, retry, and telemetry ([ADR-032](docs/02-architecture/decisions/ADR-032-unified-http-client.md)).
- **Strict Governance**: Comprehensive rules for schema evolution, data contracts, and operational procedures.

## Architecture Overview

BioETL follows **Hexagonal Architecture** (Ports & Adapters) with **Domain-Driven Design** patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                  INTERFACES (CLI / HTTP)                    │
├─────────────────────────────────────────────────────────────┤
│                    COMPOSITION (DI)                         │
│ entrypoints / execution_api / registry_api / runtime bootstrap│
├─────────────────────────────────────────────────────────────┤
│                     APPLICATION                             │
│ PipelineRunner │ WorkflowRunnerService │ CompositePipeline  │
├─────────────────────────────────────────────────────────────┤
│                       DOMAIN (DDD)                          │
│     Ports │ Aggregates │ Value Objects │ Entities │ Schemas │
├─────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                           │
│    ChEMBL │ PubChem │ UniProt │ Delta Lake │ Observability  │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**: External API -> Bronze (JSONL+zstd) -> Silver (Delta Lake) -> Gold (Analytics)

The interfaces layer includes both the Click CLI and lightweight HTTP-facing
operator surfaces under `src/bioetl/interfaces/http/`.

### Domain Layer (DDD)

The domain layer implements Domain-Driven Design patterns:

| Component         | Description                                                                   |
| ----------------- | ----------------------------------------------------------------------------- |
| **Ports**         | Protocol interfaces for dependency inversion (`domain/ports/`)                |
| **Aggregates**    | Domain aggregates with invariant protection (`domain/aggregates/`)            |
| **Value Objects** | Immutable domain primitives (`domain/value_objects/`)                         |
| **Entities**      | Domain entities per provider (`domain/entities/`)                             |
| **Schemas**       | Pandera `DataFrameModel` schemas for dataframe validation (`domain/schemas/`) |
**Domain Invariants & Lifecycle:**
- [Aggregate Invariants (Architecture)](docs/02-architecture/domain/aggregate-invariants.md) - Architecture-level FSM diagrams and invariants
- [Aggregate Invariants (Reference)](docs/04-reference/domain/invariants.md) - Domain rules and lifecycle documentation with examples
- [Aggregate State Machines](docs/04-reference/domain/aggregate-state-machines.md) - Published FSM transitions for Batch, PipelineRun, QuarantineEntry
- [Aggregates Overview](docs/04-reference/domain/aggregates.md) - Aggregate boundaries and responsibilities


## Supported Providers

| Provider               | Entity Types                                                                                                                                                           | Status     | Rate Limit                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------- |
| **ChEMBL**             | Activity, Assay, Assay Parameters, Molecule, Target, Target Component, Target Protein Classification, Protein Class, Cell Line, Compound Record, Publication, Publication Term/Similarity, Subcellular Fraction, Tissue | Production | 3 req/sec                             |
| **PubChem**            | Compound                                                                                                                                                               | Production | 5 req/sec                             |
| **UniProt**            | Protein                                                                                                                                                                | Production | 10 req/sec (100 req/sec with API key) |
| **UniProt ID Mapping** | ID Mapping                                                                                                                                                             | Production | Local job / no external rate limit    |
| **PubMed**             | Publication                                                                                                                                                            | Production | 3 req/sec (10 req/sec with API key)   |
| **CrossRef**           | Publication                                                                                                                                                            | Production | Polite pool                           |
| **OpenAlex**           | Publication                                                                                                                                                            | Production | 10 req/sec with API key / credit model |
| **Semantic Scholar**   | Publication                                                                                                                                                            | Production | 0.1 req/sec (1 req/sec with API key)  |

## Documentation

| Document                                                                    | Description                                                          |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [Current Architecture Inventory](docs/02-architecture/current-state-inventory.md) | Current code/config/dashboard/control-plane inventory and drift notes |
| [Current Architecture Diagrams](docs/02-architecture/current-state-diagrams.md) | Current C4, layer, medallion, run, replay, and quarantine diagrams   |
| [Pipeline Catalog](docs/04-reference/pipeline-catalog.md)                   | Current provider and composite pipeline config catalog               |
| [ChEMBL Activity Dataflow Passport](docs/02-architecture/generated/pipeline-dataflows/chembl_activity/pipeline-passport.md) | Generated source criteria, filters, processing, DQ, and layer fields |
| [Workflow Catalog](docs/04-reference/workflow-catalog.md)                   | Current declarative workflow DAG catalog                             |
| [Data Contracts Current State](docs/04-reference/contracts/data-contracts-current.md) | Current data-contract inventory and runtime contract chain       |
| [API Reference](docs/04-reference/api/index.md)                             | Full API documentation with mkdocstrings                             |
| [Architecture Decisions](docs/02-architecture/decisions/)                   | Canonical ADR index for architectural decisions                      |
| [Ubiquitous Language](docs/00-project/glossary.md)                          | Domain terminology and canonical naming                              |
| [RULES.md](docs/00-project/RULES.md)                                        | Canonical active governance and requirements                         |
| [Project Map](docs/00-project/00-map.md)                                    | Primary navigator for active project docs                            |
| [Tools Hub](docs/00-project/TOOLS.md)                                       | Current tool entry points and placement rules                        |
| [Docs Verification Guide](docs/03-guides/docs-verification.md)              | Published checklist for docs checks, drift review, and strict builds |
| [CLI Reference](docs/04-reference/cli.md)                                   | Command-line interface documentation                                 |
| [Run Manifest Contract](docs/04-reference/contracts/run-manifest-ledger.md) | Published control-plane manifest and ledger schema                   |
| [Operations Runbooks](docs/05-operations/runbooks/)                         | Incident response and procedures                                     |
| [Monitoring Docs Index](docs/03-guides/dashboards/monitoring-index.md)       | Incident-time operator dashboard navigation and triage guide     |
| [Archive Index](docs/99-archive/README.md)                                  | Repository-path historical index; not published in MkDocs nav         |

Start with [Project Map](docs/00-project/00-map.md), [RULES.md](docs/00-project/RULES.md),
[REQUIREMENTS.md](docs/01-requirements/REQUIREMENTS.md), and [Tools Hub](docs/00-project/TOOLS.md) for current guidance. Materials under
[`docs/99-archive/`](docs/99-archive/README.md) are preserved for traceability
as repository-path historical context, but active docs in `docs/00-05` remain
the source of truth.

## Repository Structure

| Path            | Role                                                                                          | Orientation                                                    |
| --------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `src/bioetl/`   | Runtime source tree organized by the five-layer architecture                                  | [Source Map](src/bioetl/README.md)                             |
| `configs/`      | Provider, entity, composite, contract, and quality configuration assets                       | [configs/README.md](configs/README.md)                         |
| `tests/`        | Unit, integration, e2e, smoke, contract, security, performance, and architecture verification | `tests/` mirrors source concerns by scope and policy surface   |
| `docs/`         | Published documentation tree: canonical active docs plus selected extended mirrors            | Start at [Project Map](docs/00-project/00-map.md)              |
| `docs/reports/` | Repo-only curated evidence and report artifacts (not published in MkDocs)                     | [docs/reports/index.md](docs/reports/index.md)                 |
| `reports/`      | Generated or working analysis outputs before curation                                         | [reports/README.md](reports/README.md)                         |
| `scripts/`      | Canonical tooling by domain, with engineering governance indexed under `scripts/engineering/` | [scripts/engineering/README.md](scripts/engineering/README.md) |

The current top-level layout is intentionally stable. Structural improvements
should usually target a specific family or navigation seam rather than trigger a
repo-wide reorganization wave.

## Quick Start

### Prerequisites

- **Python**: Version 3.12 (baseline).
- **Make**: For running automation commands.
- **uv**: Recommended package manager ([install](https://docs.astral.sh/uv/getting-started/installation/)).
- **Docker**: Optional, only for `docker-compose` extras such as Neo4j and monitoring; not required for the Local-Only runtime. See [Docker Quick Start](docs/DOCKER_QUICKSTART.md) and [Docker Setup](docs/DOCKER_SETUP.md) for adjunct helper usage.
- **Node.js**: Optional, for Mermaid diagram rendering and related docs tooling.

The supported dependency/bootstrap path is uv-first. `pip` remains a manual
fallback when `uv` is unavailable.

### Runtime compatibility policy

- **Python runtime baseline: 3.12** for local development, onboarding, and CI defaults.
- **Supported versions: Python 3.12 and 3.13** (see `pyproject.toml` classifiers).
- The **source of truth** for Python runtime compatibility is `pyproject.toml` (`requires-python` and classifiers).
- Any docs or scripts mentioning older Python versions (3.10/3.11) should be treated as deprecated and updated before use.

### Installation

#### Option A: Supported uv / Script-Based Setup (Recommended)

Use the maintained uv + script entrypoints for local bootstrap:

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
uv sync --extra dev --extra tests --extra tracing
uv run python -m scripts.ops setup-plugins
```

Notes:

- Documentation site commands require the separate `docs` extra: `uv sync --extra dev --extra tests --extra tracing --extra docs` or `pip install -e ".[dev,tests,tracing,docs]"`.
- `uv run python -m scripts.ops setup-plugins` configures local pytest and pre-commit tooling.
- Hook-only reinstall remains available through `bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only`.
- If you use Codex, GitHub Copilot, or Devin MCP, run `uv run python -m scripts.engineering.dev setup-mcp` after install. If you activated the OS-appropriate environment instead of using `uv`, `python -m scripts.engineering.dev setup-mcp` is also valid.
- For Devin CLI `v3000.3+`, run `make devin-check` once and `make devin` to
  launch from the repository root. Start the optional daily shared MCP plane
  explicitly with `make devin-mcp-start` when MCP-heavy work requires it.
- For docs verification and strict site builds, use the published [Docs Verification Guide](docs/03-guides/docs-verification.md).

#### Mixed Windows + WSL Development

If you use the same checkout from both Windows PowerShell and WSL, keep the
virtual environments separate. A Linux `.venv` is not valid in PowerShell, and
a Windows `.venv` is not valid in WSL.

Use:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
```

This creates:

```text
.venv-win  # Windows PowerShell
$HOME/.venvs/bioetl  # WSL/Linux by default
```

Then use the OS-specific wrappers:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
bash scripts/engineering/dev/run_mypy.sh
```

On mixed Windows + WSL checkouts, keep the PowerShell wrapper at `-n 1` unless
you intentionally override `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS`; the Windows
runtime caps the safe default worker count to avoid socket buffer exhaustion.

#### Option B: Manual Setup Without `make`

1. **Clone and Install**:
   Initialize the virtual environment and install project dependencies.

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Preferred manual path
uv sync --extra dev --extra tests --extra tracing
# Add --extra docs if you need MkDocs/site builds
uv sync --extra dev --extra tests --extra tracing --extra docs

# Fallback without uv: use an installed Python 3.12+ interpreter.
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,tests,tracing,docs]"
```

1. **Configure Environment** *(optional)*:
   Copy the example configuration if you need API keys for providers.

   ```bash
   cp .env.example .env
   ```

   AI/runtime agents must not create or edit `.env` files without explicit
   per-task approval; this copy step is for a human local setup session.

   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`. UniProt remains public by default and `BIOETL_UNIPROT_API_KEY` is optional. OpenAlex production-like runs should set `BIOETL_OPENALEX_API_KEY`; `BIOETL_OPENALEX_EMAIL` is only contact attribution and does not replace the API key.*

   **Environment Variables:**

   | Variable                                   | Description                                                 | Default                   |
   | ------------------------------------------ | ----------------------------------------------------------- | ------------------------- |
   | **Core**                                   |                                                             |                           |
   | `BIOETL_ENV`                               | Environment (`dev` / `staging` / `prod`)                    | `dev`                     |
   | `BIOETL_DATA_DIR`                          | Base directory for Bronze/Silver/Gold data                  | `data`                    |
   | `BIOETL_DEBUG`                             | Enable debug features                                       | `false`                   |
   | `BIOETL_TEST_MODE`                         | Use fixtures instead of real APIs                           | `false`                   |
   | **Pipeline**                               |                                                             |                           |
   | `BIOETL_PIPELINE__BATCH_SIZE`              | Records per batch write (1–10000)                           | `100`                     |
   | `BIOETL_PIPELINE__CHECKPOINT_INTERVAL`     | Save checkpoint every N records (≥100)                      | `1000`                    |
   | `BIOETL_PIPELINE__MAX_CONCURRENT_BATCHES`  | Max concurrent batch writes (1–16)                          | `4`                       |
   | `BIOETL_PIPELINE__HEARTBEAT_INTERVAL`      | Lock heartbeat interval in seconds (5–60)                   | `30`                      |
   | **Provider API Keys**                      |                                                             |                           |
   | `BIOETL_UNIPROT_API_KEY`                   | Optional UniProt API key (higher rate limits)               | —                         |
   | `BIOETL_PUBMED_API_KEY`                    | NCBI E-utilities API key                                    | —                         |
   | `BIOETL_PUBMED_EMAIL`                      | Email for NCBI tool identification                          | —                         |
   | `BIOETL_OPENALEX_API_KEY`                  | OpenAlex API key for production-like runs                   | —                         |
   | `BIOETL_OPENALEX_EMAIL`                    | Optional OpenAlex contact email for request attribution     | —                         |
   | `BIOETL_SEMANTICSCHOLAR_API_KEY`           | Semantic Scholar API key                                    | —                         |
   | `BIOETL_CROSSREF_EMAIL`                    | Email for Crossref polite pool                              | —                         |
   | **Security**                               |                                                             |                           |
   | `BIOETL_PII_SALT_CURRENT`                  | Salt for PII hashing (≥32 chars, required in prod)          | —                         |
   | `BIOETL_PII_SALT_NEXT`                     | Next salt for rotation                                      | —                         |
   | `BIOETL_SALT_ROTATION_ACTIVE`              | Whether salt rotation is active                             | `false`                   |
   | **Observability**                          |                                                             |                           |
   | `BIOETL_LOG_LEVEL`                         | Logging level (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`) | `INFO`                    |
   | `BIOETL_LOG_FORMAT`                        | Log format (`json` / `text`)                                | `json`                    |
   | `BIOETL_LOG_FILE`                          | Log file path                                               | `reports/logs/bioetl.log` |
   | `BIOETL_METRICS_ENABLED`                   | Enable Prometheus metrics                                   | `true`                    |
   | `BIOETL_METRICS_PORT`                      | Prometheus HTTP server port                                 | `8000`                    |
   | `BIOETL_OBSERVABILITY__TRACING_ENABLED`    | Enable OpenTelemetry tracing                                | `false`                   |
   | `BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED` | Enable data quality monitoring                              | `false`                   |
   | **Data Quality**                           |                                                             |                           |
   | `BIOETL_DQ_SOFT_THRESHOLD`                 | Warning error rate threshold                                | `0.05`                    |
   | `BIOETL_DQ_HARD_THRESHOLD`                 | Fail batch error rate threshold                             | `0.20`                    |
   | **Resilience**                             |                                                             |                           |
   | `BIOETL_CB_FAILURE_THRESHOLD`              | Consecutive errors to open circuit breaker                  | `5`                       |
   | `BIOETL_CB_RECOVERY_TIMEOUT`               | Circuit breaker recovery timeout (seconds)                  | `300`                     |
   | `BIOETL_RETRY_MAX_ATTEMPTS`                | Maximum retry attempts                                      | `3`                       |
   | `BIOETL_RETRY_MULTIPLIER`                  | Exponential backoff multiplier                              | `2.0`                     |
   | **Delta Lake**                             |                                                             |                           |
   | `BIOETL_DELTA_VACUUM_RETENTION`            | VACUUM retention (days)                                     | `7`                       |
   | `BIOETL_DELTA_FORENSIC_RETENTION`          | Forensic retention (days)                                   | `7`                       |
   | **Quarantine**                             |                                                             |                           |
   | `BIOETL_QUARANTINE_RETENTION_DAYS`         | Quarantine record retention (days)                          | `30`                      |
   | `BIOETL_QUARANTINE_PAYLOAD_MAX_SIZE`       | Max payload size (bytes)                                    | `65536`                   |

   See [`.env.example`](.env.example) for the full list with comments.

1. **Verify Installation**:
   Run tests to ensure everything works.

   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl
   uv run python -m scripts.engineering.dev run-tests cov
   ```

> **Note**: BioETL uses local file storage by default (`data/` directory). No Docker or external services required. See [Local Storage Layout](docs/03-guides/local-storage-layout.md) and [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md) for details.

### Running Pipelines

Use the OS-appropriate bootstrap path first:

```powershell
# Windows PowerShell
.\scripts\engineering\dev\setup_env_windows.ps1
.\.venv-win\Scripts\Activate.ps1
```

```bash
# WSL/Linux
bash scripts/engineering/dev/setup_env_wsl.sh
source "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/activate"
```

Then run the ETL pipeline using the CLI:

```bash
# Run incremental update for ChEMBL
python -m bioetl run --pipeline chembl_activity --run-type incremental

# Run backfill with resume capability
python -m bioetl run --pipeline chembl_activity --run-type backfill --resume

# Inspect quarantined records
python -m bioetl quarantine inspect --pipeline chembl_activity --limit 10

# List checkpoints
python -m bioetl checkpoint list --pipeline chembl_activity
```

If you do not want to activate the environment, call the interpreter directly:

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run --pipeline chembl_publication --limit 50000
```

```bash
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline chembl_publication --limit 50000
```

## Development

### Repository Hygiene

- Do **not** store domain datasets or reference data files in repository root.
- Keep machine-consumed reference datasets under semantic paths in `data/` (for example, `data/input/reference/`).
- Keep optional human-facing spreadsheet copies under `docs/04-reference/schemas/` when they are needed for documentation.
- Unified publication classifier canonical format is CSV at `data/input/reference/unified_classification.csv`; optional spreadsheet copies are non-canonical and MAY be stored in docs as needed.

### Local diagnostic artifacts

Локальные диагностические файлы (например, `git_commit_*.txt`, `*_gitshow_err.txt`, `log_test.txt`) не должны храниться в корне репозитория и не коммитятся в Git.

- Временные диагностические дампы сохраняйте в `tmp/`.
- Логи локальных запусков сохраняйте в `reports/logs/`.
- Для ad-hoc команд используйте явное перенаправление (`> reports/logs/<name>.log 2>&1` или `> tmp/<name>.txt 2>&1`).

### MCP Setup (GitHub Copilot + Codex + Qodo)

To configure the core MCP servers for both VS Code Copilot and Codex CLI:

```bash
uv run python scripts/ai/codex/setup_mcp.py
```

Windows PowerShell:

```powershell
python scripts\ai\codex\setup_mcp.py
```

What this script does:

- Writes workspace MCP config for Copilot at `.vscode/mcp.json`.
- Synchronizes `.mcp.json`, `scripts/ai/.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, `.qodo/mcp.json`, `.zed/mcp.json`, `.codex/settings.json`, `.gemini/settings.json`, Devin project settings in `.devin/config.json`, Devin MCP servers in `.devin/mcp_config.json`, and the managed MCP block in `~/.codex/config.toml`.
- Registers the current MCP set: `memory`, `filesystem`, `fetch`, `github`, `docker`, `context7`, `ast-grep`, `mcp-code-interpreter`, `prometheus`, `grafana`, `brave-search`, `neo4j-cypher`, `neo4j-memory`, `mermaid`, `deja`, `adr-analysis`, `mutmut`, `code-analyzer`, `github-actions`, `deepwiki`, and `ref`.
- Runs the pinned `mcp-server-fetch==2025.4.7` through `uvx --python 3.13`; this avoids the known stdio startup hang under CPython 3.14 in WSL while keeping the tracked config portable.
- Keeps Codex npm/uv runtime caches under the native Linux user cache (`~/.cache/bioetl-mcp`, or `$XDG_CACHE_HOME/bioetl-mcp`) so WSL package installs do not rely on atomic rename/cleanup operations on `WSL-mounted Windows paths`; tracked MCP manifests remain repo-relative.
- Uses repo-local wrappers for local and Docker-backed servers so auth and machine-local settings stay out of tracked MCP config files.
- Uses local defaults when not overridden:
  - `PROMETHEUS_URL=http://host.docker.internal:9090`
  - `GRAFANA_URL=http://host.docker.internal:3000`
  - Grafana auth prefers `GRAFANA_SERVICE_ACCOUNT_TOKEN`; otherwise it can use `GRAFANA_USERNAME` / `GRAFANA_PASSWORD`.
- Repo wrappers auto-load local secrets from untracked `.env` before launch. Existing shell variables still win over `.env`, so ad-hoc session overrides continue to work.
- Does **not** store real tokens in repository MCP files.

To refresh only the Qodo Desktop MCP config without touching Codex or Gemini settings:

```bash
uv run python scripts/ai/codex/setup_mcp.py --qodo-only
```

Windows PowerShell:

```powershell
python scripts\ai\codex\setup_mcp.py --qodo-only
```

For Qodo on Windows, make sure both `C:\Program Files\nodejs` and
`%APPDATA%\npm` are present in the user `Path` before restarting Qodo, because
the generated `.qodo/mcp.json` launches several MCP servers via `npx`.

Common MCP environment variables:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=
GITHUB_TOKEN=
PROMETHEUS_URL=http://host.docker.internal:9090
PROMETHEUS_TOKEN=
GRAFANA_URL=http://host.docker.internal:3000
GRAFANA_SERVICE_ACCOUNT_TOKEN=
GRAFANA_TOKEN=
GRAFANA_API_KEY=
BRAVE_API_KEY=
BRAVE_SEARCH_API_KEY=
DOCKERHUB_USERNAME=
HUB_PAT_TOKEN=
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
NEO4J_AUTH=neo4j/bioetl_secure_password
NEO4J_AUTH_USERNAME=
NEO4J_AUTH_PASSWORD=
```

Before using tokenized MCP tools, prefer storing secrets in the local untracked `.env` file:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN="<your_pat>"
BRAVE_API_KEY="<your_brave_key>"
GRAFANA_SERVICE_ACCOUNT_TOKEN="<your_grafana_token>"
```

Accepted alias names are normalized by the wrappers. For example:

```bash
GITHUB_TOKEN="<your_pat>"
BRAVE_SEARCH_API_KEY="<your_brave_key>"
GRAFANA_TOKEN="<your_grafana_token>"
```

Shell export also works and overrides `.env` for the current session:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="<your_pat>"
```

For Grok on Windows, HTTP MCP servers run outside the repo wrappers. Export the
already configured local `.env` values to the current process, or add
`-UserScope` and restart Grok to persist them for future sessions:

```powershell
pwsh scripts/ai/mcp/export_mcp_env_from_dotenv.ps1 -UserScope
```

On Windows, the project GitHub MCP wrapper can auto-read token from `gh auth token` when available.

### Cursor: Run Codex via Tasks

Cursor uses the same workspace tasks as VS Code. This repository includes two Codex tasks:

- `BioETL: Codex interactive (WSL)` — starts interactive Codex in WSL.
- `BioETL: Codex exec full-auto (WSL)` — prompts for a task string and runs `codex exec --full-auto`.

How to run:

1. Open Command Palette (`Ctrl+Shift+P`).
1. Run `Tasks: Run Task`.
1. Pick one of the `BioETL: Codex ...` tasks.

### IDE: Run Codex via Run and Debug

For one-click IDE launch, use `Run and Debug` configurations:

- `BioETL: Codex interactive (WSL)`
- `BioETL: Codex exec full-auto (WSL)`

How to run:

1. Open `Run and Debug` (`Ctrl+Shift+D`).
1. Select one of the `BioETL: Codex ...` configurations.
1. Press `F5`.

### Testing

The project uses `pytest` for testing with a formalized test matrix covering Unit, Integration, Contract, Property-Based, and E2E tests (see [ADR-042: Testing Strategy Matrix](docs/02-architecture/decisions/ADR-042-testing-strategy-matrix.md)).

- **Setup Plugins (pytest + pre-commit):**

  ```bash
  uv run python -m scripts.ops setup-plugins
  ```

  This command validates required pytest plugins and installs pre-commit hooks.
  Use `bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only` when you
  only need to reinstall hooks.

- **Quick Check (with dependencies auto-synced and coverage):**

  ```bash
  bash scripts/engineering/dev/run_pytest.sh
  ```

  Windows PowerShell:

  ```powershell
  .\scripts\engineering\dev\run_pytest.ps1
  ```

  The helpers assume you already bootstrapped the OS-appropriate environment with
  `uv sync --extra dev --extra tests --extra tracing` /
  `uv run python -m scripts.ops setup-plugins` or `scripts/engineering/dev/setup_env_windows.ps1` /
  `scripts/engineering/dev/setup_env_wsl.sh`. By default they run `pytest` with
  `--cov=src/bioetl --cov-report=term -q --maxfail=1`.

  `bash scripts/engineering/dev/run_pytest.sh` also calls `bash scripts/ops/launchers/codex/setup_plugins.sh --pytest-only`
  before execution, so it can self-heal missing pytest plugins in WSL/Linux.
  `.\scripts\engineering\dev\run_pytest.ps1` does not perform that bootstrap step and expects
  `.venv-win` to be prepared already.

  If you prefer to run the command manually, activate the OS-appropriate virtual environment first to avoid `--cov` argument errors:

  ```bash
  source "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/activate"
  # dev + tests_full cover pytest, VCR, architecture tooling, and benchmark extras.
  pip install -e ".[dev,tests,tests_full,tracing]"
  python -m pytest tests --cov=src/bioetl --cov-report=term
  ```

  Windows PowerShell:

  ```powershell
  .\.venv-win\Scripts\Activate.ps1
  python -m pytest tests\ --cov=src/bioetl --cov-report=term
  ```

  With `uv`, the equivalent is:

  ```bash
  uv sync --extra dev --extra tests --extra tests_full --extra tracing
  uv run python -m pytest tests --cov=src/bioetl --cov-report=term
  ```

  To include tracing and pre-commit plugin setup:

  ```bash
  uv sync --extra dev --extra tests --extra tests_full --extra tracing
  uv run python -m pre_commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
  ```

  Если `pytest` сообщает об отсутствии обязательных плагинов (`pytest-asyncio`, `pytest-cov`, `pytest-xdist`, `pytest-timeout`, `pytest-vcr`), выполните повторную синхронизацию:

  ```bash
  uv sync --extra dev --extra tests --extra tests_full --extra tracing
  ```

  Скрипт `bash scripts/engineering/dev/run_pytest.sh` проверяет наличие плагинов и автоматически доустанавливает их при необходимости. Для architecture / benchmark / observability / serialization surfaces он также требует полный capability set из extra `tests_full`.

- **Run All Tests**:

  ```bash
  uv run python -m scripts.engineering.dev run-tests cov
  ```

- **Run Unit Tests Only** (Fast, no I/O):

  ```bash
  uv run python -m scripts.engineering.dev run-tests unit
  ```

- **Run Integration Tests** (Uses VCR.py cassettes, no network required):

  ```bash
  uv run python -m scripts.engineering.dev run-tests integration
  ```

- **Run Architecture Tests**:

  ```bash
  uv run python -m scripts.engineering.dev run-tests arch
  ```

### Local Tooling

- **Configure project plugin/test tooling**:

  ```bash
  uv run python -m scripts.ops setup-plugins
  ```

  This runs the supported local setup launcher for project plugin and test tooling.

### Code Quality

Strict quality standards are enforced using `ruff`, `mypy`, and other tools.

- **Linting & Formatting**:

  ```bash
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl
  ```

- **Debt and complexity guardrails**:

  ```bash
  uv run python -m scripts.engineering.qa report-debt-governance-gates --check
  ```

  The lint path uses the live Ruff + mypy toolchain directly; the debt command
  runs the published fail-fast debt-governance rollup.

### Documentation

Validate published documentation surfaces:

```bash
python -m scripts.docs check-links --links --specs --configs
python -m scripts.docs check-drift --ports --classes
python -m scripts.docs check-docstrings --summary
```

If a local docs server is needed, use the separate docs environment described in
`docs/03-guides/quick-start.md`; the current Makefile publishes validation
commands, not a local docs server target.

## Project Structure

```
.
├── configs/                  # YAML pipeline configurations
├── docs/                     # Documentation (Architecture, Guides, Runbooks)
│   ├── 02-architecture/      # Layer docs, diagrams, ADR index
│   ├── 00-project/
│   │   ├── glossary.md       # Ubiquitous Language glossary
│   │   └── RULES.md          # Project governance (see file header)
│   └── ...
├── src/
│   └── bioetl/
│       ├── domain/           # Pure business logic (DDD), NO I/O
│       │   ├── ports/        # Protocol interfaces (Ports)
│       │   ├── aggregates/   # DDD Aggregates with invariants
│       │   ├── value_objects/ # Immutable domain primitives
│       │   ├── entities/     # Domain entities per provider
│       │   ├── schemas/      # Pydantic/Pandera validation schemas
│       │   └── exceptions/   # Classified exceptions (Critical/Recoverable/DQ)
│       ├── application/      # Pipeline orchestration & services
│       │   ├── core/         # Runner, batch execution, lifecycle, preflight/postrun, transformer runtime
│       │   ├── pipelines/    # ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar (+ common utilities)
│       │   └── services/     # Application services (lifecycle, vacuum, cleanup)
│       ├── composition/      # Composition Root (public seams, bootstrap, factories)
│       │   ├── bootstrap/    # Runtime and CLI bootstrap assembly
│       │   ├── factories/    # Pipeline, storage, data source, service factories
│       │   ├── providers/    # Provider registry and loading lifecycle
│       │   ├── runtime_builders/ # Leaf builders for runner inputs and observability
│       │   ├── services/     # Thin re-exports for metadata/versioning helpers
│       │   ├── entrypoints.py # Stable broad public seam
│       │   ├── composite_api.py # Composite runtime facade
│       │   ├── control_plane_api.py # Control-plane API seam
│       │   ├── execution_api.py # Narrow execution API
│       │   ├── health_api.py # Health and diagnostics seam
│       │   ├── maintenance_api.py # Maintenance API seam
│       │   ├── observability_api.py # Observability facade
│       │   ├── registry_api.py # Registry API seam
│       │   └── resources_api.py # Narrow checkpoint/quarantine API
│       ├── infrastructure/   # Adapters (API clients, Delta Lake, Storage)
│       │   ├── adapters/     # HTTP clients with unified resilience
│       │   ├── storage/      # Bronze/Silver/Gold writers
│       │   ├── locking/      # In-memory locks (MemoryLock)
│       │   └── observability/ # Metrics, tracing, logging
│       └── interfaces/       # External interfaces
│           ├── cli/          # Click CLI commands
│           └── http/         # HTTP health server and request/response types
├── tests/                    # Unit, integration, contract, architecture, E2E, smoke, performance, security, golden/snapshot, benchmark, fixture/helper suites
├── scripts/                  # Utility scripts (lint_terminology.py, etc.)
├── Makefile                  # Automation commands
└── pyproject.toml            # Dependencies & Tool configuration
```

### Root layout policy

Repository root is protected by `scripts/engineering/repo/audit_root_cleanliness.py`
(pre-commit + required CI job `root-hygiene`).
Only approved top-level entries are allowed.

**Core allowed root entries**:

- Source and tests: `src/`, `tests/`
- Documentation and references: `docs/`, `README.md`, `CHANGELOG.md`
- Build/configuration: `pyproject.toml`, `uv.lock`, `Makefile`, `.pre-commit-config.yaml`, `.github/`
- Operational/project assets: `configs/`, `scripts/`, `assets/`, `data/`, `reports/`, `grafana/`
- Shared AI/editor tooling surfaces approved by policy:
  `.codex/`, `.cursor/`, `.gemini/`, `.vibe/`, `.vscode/`
- Local-only tolerated tooling/cache surfaces:
  `.ai/`, `.aiassistant/`, `ai/`, `.idea/`, `.jules/`, `.junie/`, `.sonarlint/`,
  `.windsurf/`, `.agent-work/`, `.agentbridge/`, `.agents/`, `.cache/`,
  `caddy/`
- Portable PyCharm project templates: `configs/ide/pycharm/`
- Explicit exceptions listed in `.github/root-allowlist.txt`

`.codex_tmp/` is allowed only as ignored local scratch space; it must not be
committed.

**Where to place artifacts**:

- Test artifacts and run reports → `reports/`
- Logs and diagnostic dumps → `reports/` (or nested folder by run date/provider)
- Coverage artifacts (`reports/coverage/coverage.xml`, `reports/coverage/htmlcov/`, `.coverage*`) → keep out of git, generate locally/CI only
- Reference datasets and static lookup files → `docs/` (documentation reference) or `data/` (runtime/local data)

## Local-Only Deployment

BioETL uses a strictly Local-Only runtime model defined by
[ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md).
Active workflows use filesystem-backed checkpoints, local storage, and
in-memory locking. Distributed deployment, Redis locking, and Docker-based
runtime orchestration are not supported entry points for current development or
operations.

## Security

Please review our **[Security Policy](.github/SECURITY.md)** for:

- Threat model and trust boundaries
- Secret management guidelines
- Data validation architecture
- Vulnerability reporting process

## Contributing

Please read **[RULES.md](docs/00-project/RULES.md)** and **[REQUIREMENTS.md](docs/01-requirements/REQUIREMENTS.md)** before contributing.

1. Ensure tests pass: `uv run python -m scripts.engineering.dev run-tests cov`
1. Check types and linting: `uv run ruff check . && uv run ruff format --check . && uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl`
1. Follow the **RFC 2119** keywords in requirements.

## License

This project code is licensed under the MIT License. Exported or merged datasets
retain provider-specific data licensing and attribution obligations; export
sidecars include provenance, licensing, and checksum manifests so dataset
snapshots are not treated as MIT-licensed solely because the code is MIT.
