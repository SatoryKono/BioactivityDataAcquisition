# BioETL Project Instructions for GitHub Copilot

## Core Mandates
You are an expert developer on the **BioETL** project. All your suggestions MUST follow these architectural principles:

### 1. Hexagonal Architecture (Ports & Adapters)
- **Domain Layer** (`src/bioetl/domain`): PURE logic. NO imports from `infrastructure` or `application`. NO I/O.
- **Infrastructure Layer** (`src/bioetl/infrastructure`): Implementation of ports (HTTP clients, Delta Lake storage).
- **Dependency Injection**: Use Constructor Injection ONLY. Never instantiate dependencies directly inside classes.

### 2. Medallion Data Flow
- **Bronze**: Raw data (JSONL). Append-only.
- **Silver**: Cleaned, typed, deduplicated entities. Delta Lake (Merge/Upsert).
- **Gold**: Aggregated business metrics.

### 3. Engineering Standards
- **Logging**: Use `structlog`. NO `print()` statements.
- **Processing**: Prefer **Polars Lazy API** (`lf.scan_ndjson`, `lf.collect`) for large datasets.
- **Validation**: Use **Pandera** for DataFrame schema enforcement.
- **Errors**: Distinguish between Critical (fail), Recoverable (retry), and DQ (quarantine).

### 4. Naming Conventions
- Pipelines: `{source}_{entity}` (e.g., `chembl_activity`).
- Files: Snake_case. Classes: PascalCase.

### 5. Testing
- Integration tests MUST use `VCR.py` cassettes.
- Unit tests MUST be fast and logic-focused.

### 6. Security
- Never hardcode secrets. Use `.env` and `Settings` (Pydantic).
- Standardize PII using salt rotation.

Follow the instructions in `docs/00-project/rules/` for detailed coding standards.
