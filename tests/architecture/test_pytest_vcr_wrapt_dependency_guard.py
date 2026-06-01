"""Architecture guard for pytest-vcr / wrapt dependency loading.

The repository must rely on the locked ``wrapt`` dependency from the active
environment. Repo-root shadow packages or bootstrap shims hide environment
breakage and are not a supported fix path.
"""

from __future__ import annotations

import pytest

from importlib import import_module
from pathlib import Path

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_repo_root_wrapt_shadow_package_is_absent() -> None:
    """Contributors must not repair pytest-vcr by shadowing ``wrapt`` in repo root."""
    assert not (PROJECT_ROOT / "wrapt").exists(), (
        "Repo-root wrapt/ shadow package is not supported. "
        "Fix the locked environment instead of overriding the dependency import path."
    )


def test_repo_root_sitecustomize_shim_is_absent() -> None:
    """The test stack must not depend on an implicit repo-root bootstrap shim."""
    assert not (PROJECT_ROOT / "sitecustomize.py").exists(), (
        "Repo-root sitecustomize.py is not a supported pytest-vcr compatibility fix. "
        "Keep the test environment healthy via locked dependencies."
    )


def test_pytest_vcr_imports_with_locked_wrapt_dependency() -> None:
    """pytest-vcr must import against the real wrapt package from the environment."""
    pytest_vcr = import_module("pytest_vcr")
    wrapt = import_module("wrapt")

    wrapt_path = Path(getattr(wrapt, "__file__", "")).resolve()

    assert getattr(pytest_vcr, "__file__", ""), "pytest_vcr must expose an import path"
    assert wrapt_path.is_file(), f"wrapt import path is not a file: {wrapt_path}"
    assert hasattr(wrapt, "decorator"), (
        "wrapt must expose decorator for pytest-vcr compatibility"
    )
    assert wrapt_path.parent != PROJECT_ROOT / "wrapt", (
        "wrapt resolved to repo-root shadow package instead of the locked dependency"
    )
