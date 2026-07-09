# Zed Editor Configuration for BioETL Project

This directory contains Zed editor configuration for the BioETL project.

## Setup Instructions

### 1. Python Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install project with dev dependencies
pip install -e ".[dev]"
```

### 2. Zed Configuration

The configuration file in this directory should be automatically recognized by Zed:

- `settings.json` - Main Zed configuration for the project
- `README.md` - This file

**Note**: Zed automatically detects `.zed/settings.json` in the project root.

### 3. LSP Servers

Zed uses built-in LSP servers (no extra installation required):

1. **basedpyright** (Primary) - Type checking and navigation (Zed default)
2. **ruff** (Built-in) - Formatting and linting (Zed default)

The configuration explicitly disables `pylsp` to avoid conflicts.

### 4. Available Tasks

Zed tasks are configured for common operations (access via Command Palette → Tasks):

- **Format code** - `ruff format .`
- **Lint code** - `ruff check .`
- **Type check** - `mypy src/`
- **Run unit tests** - `pytest tests/unit/ -v`
- **Run integration tests** - `pytest tests/integration/ -v`
- **Run architecture tests** - `pytest tests/architecture/ -v`
- **Run E2E smoke tests** - `pytest -m e2e_smoke -v`
- **Security scan** - `bandit -r src/`
- **Coverage report** - `pytest --cov=src/bioetl --cov-report=html`
- **Architecture compliance** - `import-linter --config .importlinter`

### 5. Project Structure Navigation

Key directories to add to Zed favorites:

- `src/bioetl/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
- `configs/` - Pipeline configurations
- `scripts/` - Utility scripts

### 6. Architecture Layers

The project follows a layered architecture:

- `domain/` - Business logic and entities
- `application/` - Application services
- `infrastructure/` - External integrations
- `interfaces/` - Port definitions
- `composition/` - Dependency injection

### 7. Formatting and Linting

- **Line length**: 88 characters (soft), 120 characters (hard limit)
- **Formatter**: Ruff (replaces Black + isort)
- **Linter**: Ruff + MyPy (strict mode)
- **Type checking**: MyPy with strict mode enabled
- **Format on save**: Enabled in Zed configuration

### 8. Testing

Test markers used in the project:

- `unit` - Fast unit tests (no I/O)
- `integration` - Integration tests (may use I/O)
- `e2e` - End-to-end tests (slow, local-only)
- `e2e_smoke` - PR-blocking E2E smoke subset
- `architecture` - Architecture compliance tests
- `contract` - Contract tests (API compatibility)
- `security` - Security tests
- `vcr` - VCR.py recorded HTTP interactions

### 9. Snippets

**Note**: Zed does not automatically load snippets from `.zed/snippets.json`. 

To use code snippets in Zed:
1. Open Zed settings (Ctrl+,)
2. Navigate to snippets
3. Create language-specific snippet files (e.g., `python.json`)
4. Add custom snippets based on project patterns

### 10. Troubleshooting

#### LSP not working
- Ensure virtual environment is activated
- Zed automatically detects `.venv` via toolchain selector
- Check that `basedpyright` and `ruff` are enabled in settings

#### Tasks not showing
- Reload Zed workspace (Ctrl+Shift+R)
- Check that `.zed/settings.json` is in project root
- Verify task syntax is correct (flat array, not nested)

#### Formatting not working
- Ensure Ruff is installed: `pip list | grep ruff`
- Check that format-on-save is enabled
- Verify Python language server is set to use Ruff

#### Type checking issues
- MyPy is configured in `pyproject.toml` with strict mode
- Run type check manually via task: "Type check"
- Check mypy overrides for external libraries

## Additional Resources

- Project documentation: `docs/`
- Architecture decisions: `docs/02-architecture/decisions/`
- Rules and requirements: `docs/00-project/RULES.md`
- Testing standards: `docs/styleguide/05-testing-standards.md`
- Zed documentation: https://zed.dev/docs/
