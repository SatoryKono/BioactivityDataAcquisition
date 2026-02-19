# BioETL AI Project Invariants (Source of Truth)

> **MANDATORY FOR ALL AGENTS:** Read this before any task.

## 1. Hexagonal Architecture (The Strict Boundary)

- **Domain (`src/bioetl/domain`)**: Pure logic, Protocols (Ports). NO I/O, NO `infrastructure` imports.
- **Application (`src/bioetl/application`)**: Orchestration only. No implementation details.
- **Infrastructure (`src/bioetl/infrastructure`)**: Adapters (HTTP, Delta Lake). Implements Ports.
- **Composition (`src/bioetl/composition`)**: Dependency injection root.

## 2. Determinism & Data Integrity

- **Identical In â†’ Identical Out**: Fixed column order, stable row sort, UTC timestamps.
- **Validate-before-write**: Use `Pandera` schemas in Domain. No write without validation.
- **Atomic Writes**: Ensure data consistency (no partial writes if possible).

## 3. Tooling & Style

- **Python**: 3.12+ (uv managed), ruff for linting/formatting, mypy --strict.
- **Logging**: Use `UnifiedLogger` (structured JSON). NEVER use `print()`.
- **Secrets**: `pydantic-settings` only. No hardcoded keys.
- **Docs**: Google-style docstrings with types.

## 4. Testing (Target Coverage: 85%)

- **Unit**: Fast, no network. Use `respx` for HTTP. Marker: `@pytest.mark.unit`.
- **Integration**: Use `VCR.py` for API recording. Marker: `@pytest.mark.integration`.
- **Async**: Use `@pytest.mark.asyncio(scope="function")`.

## 5. Commit Standard

- **Conventional Commits**: `feat(scope): description`, `fix(scope): description`.

## Reference Rules (Full versions)

- Core: `.aiassistant/rules/00-core-principles.md`
- Naming: `.aiassistant/rules/12-entity-naming-policy.md`
- Documentation: `.aiassistant/rules/13-documentation-standards.md`
