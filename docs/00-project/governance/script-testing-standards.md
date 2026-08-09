______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Script Testing Standards

## Purpose

This document defines the testing standards for all scripts in the BioETL project to ensure quality, reliability, and maintainability across the codebase.

## Scope

This policy applies to all script files in the `scripts/**` directory, including:
- Python scripts (`.py`)
- Shell scripts (`.sh`)
- PowerShell scripts (`.ps1`)
- Batch files (`.bat`)

## Current State Analysis

### Python Scripts
- **Total:** 406 scripts
- **With tests:** 109 scripts (26.8%)
- **Without tests:** 297 scripts (73.2%)

### Test Coverage
- **Total test files:** 111 test files
- **Test coverage:** Currently focused on infrastructure and ops scripts
- **Coverage reporting:** Enabled for `src/bioetl` and `scripts`

## Python Script Testing Standards

### Test Framework

**Convention:** pytest

**Pattern:**
```python
"""Tests for script_name.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.module.script_name import function_to_test

pytestmark = pytest.mark.unit


class TestFunctionToTest:
    """Test function_to_test functionality."""

    def test_function_success(self, tmp_path: Path) -> None:
        """Test successful function execution."""
        # Arrange
        test_data = {"key": "value"}

        # Act
        result = function_to_test(test_data)

        # Assert
        assert result is not None
        assert result["key"] == "value"

    def test_function_error_handling(self) -> None:
        """Test function error handling."""
        # Arrange
        invalid_data = None

        # Act & Assert
        with pytest.raises(ValueError):
            function_to_test(invalid_data)
```

### Required Elements

1. **Test file naming:** `test_<script_name>.py`
2. **Test class naming:** `Test<ClassName>` or `Test<FunctionName>`
3. **Test method naming:** `test_<scenario>`
4. **Docstrings:** Each test must have a descriptive docstring
5. **Markers:** Use `pytest.mark.unit` for unit tests

### Test Categories

#### Unit Tests
- Test individual functions in isolation
- Mock external dependencies (API calls, file system)
- Fast execution (< 1 second per test)
- No network or I/O operations

#### Integration Tests
- Test script workflows end-to-end
- Use real file system (temp directories)
- Test with real configuration files
- Slower execution (1-10 seconds per test)

#### Contract Tests
- Test script interfaces and contracts
- Validate input/output schemas
- Test error handling and edge cases
- Medium execution time

### Mocking Strategy

#### External Dependencies
```python
from unittest.mock import Mock, patch

@patch("scripts.module.script_name.external_function")
def test_with_mock(mock_external):
    """Test with mocked external dependency."""
    mock_external.return_value = "mocked_value"
    result = function_under_test()
    assert result == "expected"
```

#### File System Operations
```python
def test_with_temp_file(tmp_path: Path) -> None:
    """Test with temporary file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    result = process_file(test_file)
    assert result is not None
```

## Shell Script Testing Standards

### Test Framework

**Convention:** bats (Bash Automated Testing System) or pytest with shell execution

**Pattern:**
```python
"""Tests for script_name.sh."""

from __future__ import annotations

from pathlib import Path
import subprocess
import pytest

pytestmark = pytest.mark.unit


class TestScriptName:
    """Test script_name.sh functionality."""

    def test_script_execution(self, tmp_path: Path) -> None:
        """Test script execution with valid arguments."""
        script_path = Path("scripts/module/script_name.sh")
        result = subprocess.run(
            ["bash", str(script_path), "arg1", "arg2"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "expected output" in result.stdout

    def test_script_error_handling(self) -> None:
        """Test script error handling with invalid arguments."""
        script_path = Path("scripts/module/script_name.sh")
        result = subprocess.run(
            ["bash", str(script_path), "invalid_arg"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
```

## Test Coverage Requirements

### Coverage Targets

- **Critical scripts:** ≥ 80% coverage
- **High-priority scripts:** ≥ 70% coverage
- **Medium-priority scripts:** ≥ 60% coverage
- **Low-priority scripts:** ≥ 50% coverage

### Coverage Reporting

Coverage is enabled for both `src/bioetl` and `scripts` in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/bioetl", "scripts"]
branch = true
relative_files = true
```

### Coverage Commands

```bash
# Run tests with coverage
pytest --cov=scripts --cov-report=html

# Generate coverage report
pytest --cov=scripts --cov-report=term-missing

# Check coverage threshold
pytest --cov=scripts --cov-fail-under=70
```

## Test Directory Structure

### Python Tests
```
tests/unit/scripts/
├── ai/
│   ├── codex/
│   │   └── test_doctor.py
│   └── mcp/
│       └── test_check_env_keys.py
├── ops/
│   ├── data/
│   │   ├── conftest.py
│   │   ├── test_check_delta_integrity.py
│   │   └── test_extract_null_fields.py
│   └── observability/
└── docs/
    ├── conftest.py
    ├── test_docs_parity_check.py
    └── test_generate_adr_registry.py
```

### Shell Tests
```
tests/unit/scripts/
├── ops/
│   └── test_deploy_bioetl.sh
└── engineering/
    └── test_run_tests.sh
```

## Critical Scripts Testing Priority

### Phase 1: High-Priority Scripts (Week 2-3)
- `scripts/ai/codex/doctor.py` - AI runtime diagnostics
- `scripts/ai/codex/setup_mcp.py` - MCP configuration
- `scripts/ai/codex/sync_native_skills.py` - Skills synchronization
- `scripts/engineering/dev/run_tests.py` - Test execution
- `scripts/engineering/repo/check_scripts_inventory.py` - Script inventory

### Phase 2: Medium-Priority Scripts (Week 4-5)
- `scripts/ai/mcp/_check_env_keys.py` - Environment validation
- `scripts/ai/mcp/_patch_grok_mcp_tokens.py` - Token management
- `scripts/ops/data/validate_data_dir.py` - Data validation
- `scripts/ops/migrations/validate_sunset_dates.py` - Migration validation

### Phase 3: Low-Priority Scripts (Week 6-7)
- Helper scripts and utilities
- Legacy/deprecated scripts
- One-off maintenance scripts

## Test Quality Standards

### Test Characteristics

1. **Independence:** Tests should not depend on each other
2. **Determinism:** Tests should produce consistent results
3. **Speed:** Unit tests should be fast (< 1 second)
4. **Clarity:** Test names should describe what they test
5. **Maintainability:** Tests should be easy to understand and modify

### Anti-Patterns

- ❌ Tests that depend on execution order
- ❌ Tests with hardcoded paths
- ❌ Tests that sleep or wait indefinitely
- ❌ Tests with complex setup/teardown
- ❌ Tests that test implementation details

## CI Integration

### Pre-commit Hooks

Add pre-commit hooks to run tests:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: run-script-tests
      name: Run script unit tests
      entry: pytest tests/unit/scripts/ -v
      language: system
      files: \.py$
      types: [python]
```

### CI Validation

Add CI validation for script tests:

```yaml
# .github/workflows/script-tests.yml
name: Script Tests
on: [pull_request]
jobs:
  test-scripts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run script tests
        run: pytest tests/unit/scripts/ --cov=scripts --cov-report=xml
```

## Documentation Requirements

### Test Documentation

Each test file should include:
- Purpose of the tests
- What functionality is being tested
- Any important test setup or teardown requirements
- Dependencies on external systems or data

### Test Reports

Generate test reports with:
- Test execution summary
- Coverage percentages
- Failed test details
- Performance metrics

## Related Documents

- [Script Documentation Standards](script-documentation-standards.md) - Documentation standards for scripts
- [Script Naming Conventions](script-naming-conventions.md) - Naming standards for scripts
- [Script Inventory Audit](../../reports/scripts_inventory_audit_report.md) - Overall script inventory
- [pytest Documentation](https://docs.pytest.org/)

## Revision History

- **2026-08-09:** Initial testing standards definition based on script audit
