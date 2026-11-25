"""Run temporary-file tests with their temporary directory as the trust root."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def temporary_working_directory(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep pytest temporary paths inside the process working directory."""
    if "tmp_path" in request.fixturenames:
        path: Path = request.getfixturevalue("tmp_path")
        monkeypatch.chdir(path)
