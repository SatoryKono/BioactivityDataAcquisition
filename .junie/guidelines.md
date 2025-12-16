# BioETL Project Guidelines

## 1. Build & Configuration Instructions

### Prerequisites

- **Python**: Version 3.11 or higher.
- **Docker**: Required for local infrastructure (Postgres, Redis, MinIO).
- **Make**: For running automation commands (or use specific commands from `Makefile`).

### Setup

1. **Install Dependencies**:
   Initialize the virtual environment and install project dependencies (including dev tools).
   ```bash
   make install
   ```
   *Under the hood: Creates `.venv`, updates pip, and runs `pip install -e ".[dev]"`. @see `pyproject.toml`.*

2. **Start Infrastructure**:
   Launch local services via Docker Compose.
   ```bash
   make docker-up
   ```
   *Services: Postgres, Redis, MinIO.*

3. **Environment Variables**:
   Ensure you have a `.env` file or exported variables if needed.
   Copy example config if available:
   ```bash
   cp .env.example .env
   ```
   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`.*

## 2. Testing Information

The project uses `pytest` for testing, split into **Unit** (fast, no I/O) and **Integration** (I/O, VCR.py).

### Running Tests

- **Run All Tests**:
  ```bash
  make test
  ```
- **Run Unit Tests Only**:
  ```bash
  make test-unit
  ```
- **Run Integration Tests**:
  ```bash
  make test-integration
  ```
- **Run Architecture Tests**:
  ```bash
  make arch-test
  ```

### Adding New Tests

#### Guidelines

1. **Domain Layer (`src/bioetl/domain`)**:
  - MUST be tested with **Unit Tests** only.
  - MUST NOT use mocks for external libraries; use in-memory fakes/stubs if needed.
  - Purity: No I/O allowed.
2. **Infrastructure Layer**:
  - Use **Integration Tests**.
  - Use `vcrpy` to record/replay HTTP interactions.
  - Fixtures are available in `tests/conftest.py` (e.g., `redis_client`, `minio_client`).

#### Example: Simple Unit Test

Create a file `tests/unit/test_example.py`:

```python
import pytest
from bioetl.domain.types import RunType


@pytest.mark.unit
def test_run_type_enum() -> None:
  """Demonstrate a simple unit test for domain logic."""
  # Arrange
  run_type = RunType.INCREMENTAL

  # Act & Assert
  assert run_type.value == "incremental"
  assert RunType("backfill") == RunType.BACKFILL
```

### Configuration

- **Pytest Config**: `[tool.pytest.ini_options]` in `pyproject.toml`.
- **Coverage**: Configured to check `src/bioetl` with a minimum threshold (80%).

## 3. Additional Development Information

### Code Style & Quality

The project enforces strict quality standards using `ruff` and `mypy`.

- **Linting & Formatting**:
  ```bash
  make lint      # Check only
  make lint-fix  # Auto-fix and format
  ```
- **Type Checking**:
  ```bash
  make typecheck # Strict mypy
  ```
- **Pre-commit Hooks**:
  Install hooks to run checks automatically before commit:
  ```bash
  pre-commit install
  ```

### Architecture Overview

- **Medallion Architecture**: Bronze (Raw/JSONL) -> Silver (Delta/Parquet) -> Gold (Business/Aggregated).
- **Hexagonal/Clean Architecture**:
  - `domain/`: Pure business logic and interfaces (Ports).
  - `application/`: Orchestration and use cases.
  - `infrastructure/`: Adapters (API clients, DB repos).
- **Strict Dependency Rules**: Domain cannot import from Infrastructure. Checked via `import-linter`.

### Documentation

- Build and serve local documentation:
  ```bash
  make docs-serve
  ```
