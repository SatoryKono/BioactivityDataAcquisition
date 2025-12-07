from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
import yaml


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def src_root(project_root: Path) -> Path:
    return project_root / "src"


@pytest.fixture(scope="session")
def bioetl_root(src_root: Path) -> Path:
    return src_root / "bioetl"


@pytest.fixture(scope="session")
def configs_root(project_root: Path) -> Path:
    return project_root / "configs"


@pytest.fixture(scope="session")
def docs_root(project_root: Path) -> Path:
    return project_root / "docs"


def iter_python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}

