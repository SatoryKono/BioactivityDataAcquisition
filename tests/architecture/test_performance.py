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
"""Architecture test: Performance optimization enforcement."""

import pytest

import ast
from pathlib import Path

pytestmark = pytest.mark.architecture

STORAGE_DIR = Path("src/bioetl/infrastructure/storage")
BATCH_WRITER = Path("src/bioetl/application/core/batch_writer.py")

# Files allowed to use json (e.g. for compatibility or specific exceptions)
# Currently none as we want strict orjson usage in storage layer
ALLOWED_FILES: set[str] = {
    "bronze_writer.py",  # Uses json for metadata and validation
    "silver_writer.py",  # Uses json for Delta Lake serialization
}


def _json_import_violations(py_file: Path) -> list[str]:
    """Collect forbidden json imports for a single Python file."""
    violations: list[str] = []
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "json":
                    violations.append(f"{py_file.name}:{node.lineno}: import json")
        elif isinstance(node, ast.ImportFrom) and node.module == "json":
            violations.append(f"{py_file.name}:{node.lineno}: from json import ...")

    return violations


def test_no_json_import_in_storage_layer():
    """Storage layer MUST use orjson instead of standard json.

    REQ-PERF-001: Use orjson for high-performance serialization.
    REQ-ARCH-032: Enforce orjson in storage layer.
    """
    violations: list[str] = []

    # Check infrastructure/storage directory
    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue
        violations.extend(_json_import_violations(py_file))

    # Check BatchWriter specifically as it's a hot path in application layer
    if BATCH_WRITER.exists():
        violations.extend(_json_import_violations(BATCH_WRITER))

    assert not violations, (
        "Standard 'json' library found in performance-critical modules:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse 'orjson' for high-performance serialization (REQ-PERF-001)."
    )
