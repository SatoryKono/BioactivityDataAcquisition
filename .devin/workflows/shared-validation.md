# Shared Validation Logic

This module contains shared validation logic used across multiple workflows to eliminate duplication and ensure consistency.

## Purpose

Provide a single source of truth for validation rules and checks used in:
- post-change.md
- review.md
- pre-commit.md
- qodo-sync.md

## Validation Rules

### Architecture Validation

```python
def validate_architecture_imports(file_path: str) -> bool:
    """Check import boundaries according to BioETL architecture."""
    # domain → nothing external (VIOLATION)
    # infrastructure → application (VIOLATION)
    # infrastructure → composition (VIOLATION)
    # infrastructure → interfaces (VIOLATION)
    pass
```

### Code Quality Validation

```python
def validate_code_quality(file_path: str) -> bool:
    """Check code quality standards."""
    # Type checking
    # print() instead of logger
    # Sentinel values
    # Any without justification
    pass
```

### Secrets Validation

```python
def validate_no_secrets(file_path: str) -> bool:
    """Check for exposed secrets in code/docs/configs/tests/logs."""
    # No live credentials
    # No weakened .env ignore/COPY
    # Tracked configs/** YAML: placeholders / env refs only
    pass
```

### Technical Debt Validation

```python
def validate_no_debt_increase(file_path: str) -> bool:
    """Ensure technical-debt budgets are not increased."""
    # Never increase scorecard budgets
    # Never widen linter/Sonar exclusions
    pass
```

## Common Check Functions

```bash
# Type checking
mypy src/bioetl/<scope>/ --strict --show-error-codes

# Linting
ruff check src/bioetl/<scope>/

# Architecture tests
pytest tests/architecture/ -v --tb=short

# Print statements
grep -rn "print(" src/bioetl/<scope>/ --include="*.py" | grep -v "# noqa"

# Sentinel values
grep -rn '= -1\|= "N/A"\|= "n/a"\|= "NA"' src/bioetl/<scope>/ --include="*.py"
```

## Usage in Workflows

Each workflow should import and use these shared validation functions instead of duplicating the logic:

```markdown
## Validation

Use shared validation logic from `shared-validation.md`:
- Architecture validation
- Code quality validation
- Secrets validation
- Technical debt validation
```