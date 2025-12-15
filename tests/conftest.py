import os
from pathlib import Path
import pytest
from typing import Generator

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the root directory of the project."""
    # Assuming tests/conftest.py is one level deep in tests/
    return Path(__file__).parent.parent

@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    return project_root / "src"

@pytest.fixture(scope="session")
def docs_dir(project_root: Path) -> Path:
    return project_root / "docs"

@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    return project_root / "pyproject.toml"

@pytest.fixture(scope="session")
def requirements_md(project_root: Path) -> Path:
    return project_root / "REQUIREMENTS.md"
