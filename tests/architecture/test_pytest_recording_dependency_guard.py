"""Architecture guard for pytest-recording dependency loading.

The repository must rely on the locked ``pytest-recording`` dependency from the active
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
    """Contributors must not repair pytest-recording by shadowing ``wrapt`` in repo root."""
    assert not (PROJECT_ROOT / "wrapt").exists(), (
        "Repo-root wrapt/ shadow package is not supported. "
        "Fix the locked environment instead of overriding the dependency import path."
    )


def test_repo_root_sitecustomize_shim_is_absent() -> None:
    """The test stack must not depend on an implicit repo-root bootstrap shim."""
    assert not (PROJECT_ROOT / "sitecustomize.py").exists(), (
        "Repo-root sitecustomize.py is not a supported pytest-recording compatibility fix. "
        "Keep the test environment healthy via locked dependencies."
    )


def test_pytest_recording_imports_correctly() -> None:
    """pytest-recording must import correctly from the environment."""
    pytest_recording = import_module("pytest_recording")

    assert getattr(pytest_recording, "__file__", ""), "pytest_recording must expose an import path"
