"""Windows pytest basetemp must not pre-create the leaf pytest will rm_rf."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import _configure_windows_local_basetemp

pytestmark = pytest.mark.unit


def test_windows_basetemp_is_unique_and_not_precreated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("tests.conftest.sys.platform", "win32")
    monkeypatch.setenv("BIOETL_PYTEST_TEMP_ROOT", str(tmp_path / "bioetl-pytest"))
    config = SimpleNamespace(option=SimpleNamespace(basetemp=None))

    _configure_windows_local_basetemp(config)  # type: ignore[arg-type]

    basetemp = Path(config.option.basetemp)
    assert basetemp.parent == tmp_path / "bioetl-pytest"
    assert basetemp.name.startswith("basetemp-")
    assert not basetemp.exists()


def test_windows_basetemp_honours_existing_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("tests.conftest.sys.platform", "win32")
    override = tmp_path / "explicit"
    config = SimpleNamespace(option=SimpleNamespace(basetemp=override))

    _configure_windows_local_basetemp(config)  # type: ignore[arg-type]

    assert config.option.basetemp == override
