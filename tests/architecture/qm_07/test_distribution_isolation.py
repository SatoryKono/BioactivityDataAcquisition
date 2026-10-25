"""Distribution boundaries for engineering-only quality tooling."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.architecture
def test_runtime_distribution_excludes_engineering_quality_namespace() -> None:
    """Runtime package discovery must stay rooted in src and exclude old shims."""
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_find = payload["tool"]["setuptools"]["packages"]["find"]

    assert package_find["where"] == ["src"]
    assert set(package_find["exclude"]) >= {
        "scripts",
        "scripts.*",
        "bioetl.infrastructure.quality",
        "bioetl.infrastructure.quality.*",
    }
    assert (ROOT / "scripts/engineering/quality/__init__.py").is_file()
    assert not (ROOT / "src/bioetl/infrastructure/quality").exists()
