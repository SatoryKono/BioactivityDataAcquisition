"""Architecture test: datetime.now() usage restriction.

Enforces REQ-ARCH-031: Single source of truth for timestamps.
Timestamps should be created in application layer and passed down.
"""

import ast
from pathlib import Path

import pytest

INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Files allowed to use datetime.now() for valid reasons (e.g. initial timestamp generation)
# or pending refactoring (Legacy).
ALLOWED_FILES = {
    # TODO: Refactor these to accept timestamp from context
    "unified.py",
    "operations.py",
    "lineage.py",
    "detector.py",
    "iqr.py",
    "zscore.py",
    "mad.py",
    "client.py", # chembl client
    "gold_writer.py", # Pending complete refactor of fallback
}


def test_no_datetime_now_in_infrastructure_logic():
    """Infrastructure logic MUST NOT call datetime.now() directly.

    Exceptions:
    - default factories in dataclasses (checked separately)
    - logging (handled by structlog automatically)
    """
    violations = []

    for py_file in INFRASTRUCTURE_DIR.rglob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue

        # Skip tests within infrastructure
        if "tests" in py_file.parts:
            continue

        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for datetime.now() or datetime.now(UTC)
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "now":
                        # Check if it's called on 'datetime' object
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "datetime":
                             violations.append(
                                f"{py_file.relative_to(INFRASTRUCTURE_DIR)}:{node.lineno} -> datetime.now()"
                            )
                        # Check for Class.now() where Class is datetime
                        if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "datetime":
                             violations.append(
                                f"{py_file.relative_to(INFRASTRUCTURE_DIR)}:{node.lineno} -> datetime.datetime.now()"
                            )

    assert not violations, (
        f"datetime.now() found in infrastructure layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nREQ-ARCH-031: Timestamps must be passed from Application layer (PipelineContext)."
    )
