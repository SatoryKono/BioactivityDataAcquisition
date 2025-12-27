"""Architecture test: Performance optimization enforcement."""

import ast
from pathlib import Path

STORAGE_DIR = Path("src/bioetl/infrastructure/storage")
BATCH_WRITER = Path("src/bioetl/application/core/batch_writer.py")

# Files allowed to use json (e.g. for compatibility or specific exceptions)
# Currently none as we want strict orjson usage in storage layer
ALLOWED_FILES: set[str] = {
    "bronze_writer.py",  # Uses json for metadata and validation
    "delta_writer.py",  # Uses json for Delta Lake serialization
}


def test_no_json_import_in_storage_layer():
    """Storage layer MUST use orjson instead of standard json.

    REQ-PERF-001: Use orjson for high-performance serialization.
    REQ-ARCH-032: Enforce orjson in storage layer.
    """
    violations = []

    # Check infrastructure/storage directory
    for py_file in STORAGE_DIR.glob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue

        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "json":
                        violations.append(f"{py_file.name}:{node.lineno}: import json")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "json":
                    violations.append(f"{py_file.name}:{node.lineno}: from json import ...")

    # Check BatchWriter specifically as it's a hot path in application layer
    if BATCH_WRITER.exists():
        source = BATCH_WRITER.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "json":
                        violations.append(f"{BATCH_WRITER.name}:{node.lineno}: import json")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "json":
                    violations.append(f"{BATCH_WRITER.name}:{node.lineno}: from json import ...")

    assert not violations, (
        f"Standard 'json' library found in performance-critical modules:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse 'orjson' for high-performance serialization (REQ-PERF-001)."
    )
