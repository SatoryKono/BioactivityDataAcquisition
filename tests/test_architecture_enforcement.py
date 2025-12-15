"""Architectural tests to enforce layer boundaries.

Ensures that:
1. Domain layer does not import from Application or Infrastructure.
2. Application layer does not import from Infrastructure.
3. Domain layer does not use I/O libraries.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set

import pytest

# Add src to path
SRC_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))


def get_imports(file_path: Path) -> Set[str]:
    """Extract all imported module names from a python file."""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_domain_isolation() -> None:
    """Domain layer must not import from Application or Infrastructure."""
    domain_path = SRC_ROOT / "bioetl" / "domain"

    forbidden_prefixes = [
        "bioetl.application",
        "bioetl.infrastructure",
        "bioetl.services",
        # Forbidden I/O libraries (incomplete list but good start)
        "requests",
        "httpx",
        "boto3",
        "redis",
        "sqlalchemy",
        "pymongo",
    ]

    for root, _, files in os.walk(domain_path):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            imports = get_imports(file_path)

            for imp in imports:
                for forbidden in forbidden_prefixes:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        pytest.fail(
                            f"Domain isolation violation in {file_path}:\n"
                            f"  Imported '{imp}' which is forbidden in Domain layer."
                        )


def test_application_isolation() -> None:
    """Application layer must not import from Infrastructure."""
    app_path = SRC_ROOT / "bioetl" / "application"

    forbidden_prefixes = [
        "bioetl.infrastructure",
        # "bioetl.bootstrap" is also forbidden as it depends on everything
        "bioetl.bootstrap",
    ]

    for root, _, files in os.walk(app_path):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            imports = get_imports(file_path)

            for imp in imports:
                for forbidden in forbidden_prefixes:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        pytest.fail(
                            f"Application isolation violation in {file_path}:\n"
                            f"  Imported '{imp}' which is forbidden in Application layer."
                        )

def test_no_infrastructure_in_pipelines() -> None:
    """Specific check for pipelines not importing infrastructure adapters."""
    pipelines_path = SRC_ROOT / "bioetl" / "application" / "pipelines"

    if not pipelines_path.exists():
        return

    for file_path in pipelines_path.glob("*.py"):
        imports = get_imports(file_path)
        for imp in imports:
            if "bioetl.infrastructure" in imp:
                 pytest.fail(
                    f"Pipeline {file_path.name} imports infrastructure directly: {imp}"
                )
