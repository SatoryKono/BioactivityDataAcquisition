# Contributing to BioETL

Thank you for your interest in contributing to BioETL! We follow a strict "Docs-as-Code" approach and value high code quality.

## Getting Started

1. **Environment Setup**
   ```bash
   make install
   ```

2. **Running Tests**
   ```bash
   make test
   ```

## Development Workflow

1. **Create a Feature Branch**
   - Use `feat/`, `fix/`, `refactor/` prefixes.
   - Example: `feat/add-openalex-provider`

2. **Follow Coding Standards**
   - **Typed Python**: All code must be typed (mypy strict).
   - **Docstrings**: Google Style docstrings for all modules, classes, and functions.
   - **No I/O in Domain**: Domain logic must be pure.
   - **Architecture**: Respect layer boundaries (Domain <- Application <- Infrastructure).

3. **Commit Messages**
   - Use conventional commits (e.g., `feat: add new adapter`, `fix: handle timeout`).

## Pull Request Process

1. **Pre-Checks**: Run `make check` locally before pushing.
2. **Review**: All PRs require at least one approval.
3. **CI**: All checks (tests, lint, security) must pass.

## Documentation

- `RULES.md`: The authoritative source of truth.
- `docs/`: Detailed architectural decision records (ADRs) and contracts.
- Update documentation in the same PR as code changes.

## Reporting Issues

Please use the GitHub Issue tracker and provide:
- Clear description of the problem.
- Steps to reproduce.
- Expected behavior vs actual behavior.
