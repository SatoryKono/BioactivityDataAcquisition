# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: os.environ access centralized through Settings.

REQ-ARCH-041: Environment variable access is centralized through Settings.
Composition and infrastructure layers should not access os.environ directly.
Instead, they should receive configuration via Settings (pydantic-settings).

This ensures:
- Single source of truth for configuration
- Proper validation of environment variables
- Testability through Settings injection
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Paths relative to project root
COMPOSITION_DIR = Path("src/bioetl/composition")
INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Files allowed to use os.environ - with justification.
#
# Criteria for exceptions:
# 1. The access is for infrastructure-level configuration (not business logic)
# 2. The access is required before Settings can be loaded
# 3. The access is properly documented
#
ALLOWED_COMPOSITION_FILES: set[str] = set()

ALLOWED_INFRASTRUCTURE_FILES: set[str] = {
    # _base.py (infrastructure/config/_base.py) contains Settings class which is
    # the centralized configuration. It uses pydantic-settings internally which
    # accesses os.environ. Previously was config.py, moved to config package.
    "_base.py",
    # encoders.py reads BIOETL_JSON_ENCODER to select JSON encoder at import time.
    # This is infrastructure-level configuration for encoder selection.
    "encoders.py",
    # pii_hasher.py reads BIOETL_PII_SALT_* for security-critical salt configuration.
    # Salt is security configuration that should not be passed through Settings
    # to minimize exposure in logs and error messages.
    "pii_hasher.py",
    # dq_config_loader.py uses os.environ for relaxed DQ thresholds in tests
    "dq_config_loader.py",
}


def _get_base_path(dir_path: Path) -> Path:
    """Get the base path, handling both project root and tests directory."""
    if dir_path.exists():
        return dir_path
    return Path(__file__).parent.parent.parent / dir_path


def _find_os_environ_usages(py_file: Path, base_path: Path) -> list[str]:
    """Find os.environ usages in a Python file.

    Detects patterns:
    - os.environ.get(...)
    - os.environ[...]
    - os.environ.setdefault(...)
    """
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    relative_path = py_file.relative_to(base_path)
    return [
        f"{relative_path}:{node.lineno}: {message}"
        for node in ast.walk(tree)
        for message in _iter_os_environ_messages(node)
    ]


def _iter_os_environ_messages(node: ast.AST) -> list[str]:
    if _is_os_environ_attribute(node):
        return ["os.environ"]
    if _is_os_environ_subscript(node):
        return ["os.environ[...]"]
    return []


def _is_os_environ_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_os_environ_subscript(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "environ"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "os"
    )


class TestEnvVarCentralization:
    """Tests ensuring environment variables are accessed via Settings."""

    @pytest.fixture
    def composition_python_files(self) -> list[Path]:
        """Get all Python files in composition directory."""
        base = _get_base_path(COMPOSITION_DIR)
        return list(base.rglob("*.py"))

    @pytest.fixture
    def infrastructure_python_files(self) -> list[Path]:
        """Get all Python files in infrastructure directory."""
        base = _get_base_path(INFRASTRUCTURE_DIR)
        return list(base.rglob("*.py"))

    def test_no_os_environ_in_composition(
        self, composition_python_files: list[Path]
    ) -> None:
        """Composition layer MUST NOT access os.environ directly.

        Environment variables should be read via Settings (pydantic-settings)
        and passed to factories/builders as parameters.

        This ensures:
        - Centralized configuration validation
        - Testability via Settings injection
        - Single source of truth for configuration
        """
        violations = []
        base = _get_base_path(COMPOSITION_DIR)

        for py_file in composition_python_files:
            if py_file.name in ALLOWED_COMPOSITION_FILES:
                continue

            violations.extend(_find_os_environ_usages(py_file, base))

        assert not violations, (
            "os.environ found in composition layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nEnvironment variables should be accessed via Settings "
            "(pydantic-settings) and passed as parameters. "
            "Use Settings.test_mode instead of os.environ.get('BIOETL_TEST_MODE')."
        )

    def test_no_os_environ_in_infrastructure_except_config(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Infrastructure layer SHOULD use Settings for configuration.

        The only exception is config.py which defines Settings and
        necessarily needs to access os.environ through pydantic-settings.
        """
        violations = []
        base = _get_base_path(INFRASTRUCTURE_DIR)

        for py_file in infrastructure_python_files:
            if py_file.name in ALLOWED_INFRASTRUCTURE_FILES:
                continue

            violations.extend(_find_os_environ_usages(py_file, base))

        assert not violations, (
            "os.environ found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nEnvironment variables should be accessed via Settings. "
            "Add required configuration to Settings class in config.py."
        )

    def test_allowed_composition_files_still_exist(
        self, composition_python_files: list[Path]
    ) -> None:
        """Verify that files in ALLOWED_COMPOSITION_FILES actually exist."""
        existing_names = {f.name for f in composition_python_files}
        missing = ALLOWED_COMPOSITION_FILES - existing_names

        assert not missing, (
            f"ALLOWED_COMPOSITION_FILES contains non-existent files: {missing}. "
            "Remove stale entries from the allowed list."
        )

    def test_allowed_infrastructure_files_still_exist(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Verify that files in ALLOWED_INFRASTRUCTURE_FILES actually exist."""
        existing_names = {f.name for f in infrastructure_python_files}
        missing = ALLOWED_INFRASTRUCTURE_FILES - existing_names

        assert not missing, (
            f"ALLOWED_INFRASTRUCTURE_FILES contains non-existent files: {missing}. "
            "Remove stale entries from the allowed list."
        )
