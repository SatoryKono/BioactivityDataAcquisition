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
"""Architecture guard for VCR replay runtime loading.

The repository must not rely on repo-root shadow packages or bootstrap shims to
repair HTTP cassette replay. Either ``pytest-recording`` or the repo-local
``vcrpy`` fallback runtime must be available from the active environment.
"""

from __future__ import annotations

import sys

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


def test_vcr_replay_runtime_imports_correctly() -> None:
    """One supported VCR replay runtime must import correctly from the environment."""
    if "vcr.matchers" in sys.modules and "pytest_recording" not in sys.modules:
        replay_runtime = import_module("vcr")
        assert getattr(replay_runtime, "__file__", ""), (
            "Supported VCR replay runtime must expose an import path"
        )
        return

    try:
        replay_runtime = import_module("pytest_recording")
    except ModuleNotFoundError:
        replay_runtime = import_module("vcr")

    assert getattr(replay_runtime, "__file__", ""), (
        "Supported VCR replay runtime must expose an import path"
    )
