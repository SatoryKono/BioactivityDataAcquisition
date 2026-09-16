"""Behavioral tests for bounded storage path probes."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.storage.support.path_io import path_exists_bounded

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("exists", [False, True])
def test_path_exists_bounded_uses_direct_probe_when_timeout_is_disabled(
    exists: bool,
) -> None:
    with patch.object(Path, "exists", return_value=exists) as probe:
        assert path_exists_bounded("artifact.json", timeout_seconds=0) is exists
    probe.assert_called_once_with()


def test_path_exists_bounded_maps_direct_probe_oserror_to_false() -> None:
    with patch.object(Path, "exists", side_effect=OSError("unavailable")):
        assert path_exists_bounded("artifact.json", timeout_seconds=-1) is False


@pytest.mark.parametrize("exists", [False, True])
def test_path_exists_bounded_returns_background_probe_result(exists: bool) -> None:
    with patch.object(Path, "exists", return_value=exists) as probe:
        assert path_exists_bounded("artifact.json", timeout_seconds=0.1) is exists
    probe.assert_called_once_with()


@pytest.mark.parametrize(
    "error",
    [concurrent.futures.TimeoutError(), OSError("unavailable")],
)
def test_path_exists_bounded_maps_bounded_probe_failures_to_false(
    error: BaseException,
) -> None:
    future = MagicMock()
    future.result.side_effect = error
    pool = MagicMock()
    pool.__enter__.return_value.submit.return_value = future

    with patch(
        "bioetl.infrastructure.storage.support.path_io.concurrent.futures.ThreadPoolExecutor",
        return_value=pool,
    ):
        assert path_exists_bounded("artifact.json", timeout_seconds=0.1) is False

    future.result.assert_called_once_with(timeout=0.1)
