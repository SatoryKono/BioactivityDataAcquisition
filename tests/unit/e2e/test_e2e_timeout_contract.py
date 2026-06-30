"""Unit guards for E2E timeout-budget invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import conftest as e2e_conftest

pytestmark = pytest.mark.unit


def test_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Windows pytest timeout must exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="win32")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )

    assert outer_timeout > inner_timeout
    assert inner_timeout == 180


def test_windows_pipeline_matrix_timeout_stays_between_inner_and_outer() -> None:
    """Windows matrix timeout must not preempt the governed Silver timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="win32")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="win32",
            env={},
        )
    )

    assert outer_timeout > matrix_timeout > inner_timeout
    assert matrix_timeout == pytest.approx(240.0)


def test_windows_e2e_plain_delta_writes_are_process_isolated() -> None:
    """Windows E2E plain Delta writes use process isolation for bounded timeouts."""
    assert (
        e2e_conftest._resolve_e2e_plain_write_process_isolation(platform="win32")
        is True
    )


def test_windows_e2e_temp_root_prefers_local_appdata_temp(tmp_path: Path) -> None:
    """Windows E2E sandboxes should prefer a local temp root over TMP/TEMP."""
    local_appdata = tmp_path / "local_appdata"
    local_temp = local_appdata / "Temp"
    local_temp.mkdir(parents=True)
    fallback = tmp_path / "slow_temp"
    fallback.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(fallback),
        env={"LOCALAPPDATA": str(local_appdata)},
    )

    assert resolved == local_temp


def test_windows_e2e_temp_root_honors_explicit_override(tmp_path: Path) -> None:
    """Operators may force an explicit sandbox root when diagnosing I/O issues."""
    override = tmp_path / "override_temp"
    override.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(tmp_path / "fallback"),
        env={"BIOETL_E2E_TEMP_ROOT": str(override)},
    )

    assert resolved == override


def test_windows_e2e_temp_root_falls_back_without_local_appdata(tmp_path: Path) -> None:
    """Windows E2E uses the process tempdir when no local-app-data temp exists."""
    fallback = tmp_path / "fallback_temp"
    fallback.mkdir()

    resolved = e2e_conftest._resolve_e2e_temp_root(
        platform="win32",
        fallback_tmp=str(fallback),
        env={},
    )

    assert resolved == fallback


def test_non_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Non-Windows pytest timeout must also exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="linux"
    )

    assert outer_timeout > inner_timeout
    assert outer_timeout == 120
    assert inner_timeout == 90


def test_non_windows_pipeline_matrix_timeout_stays_between_inner_and_outer() -> None:
    """Non-Windows matrix timeout keeps the existing 105s default contract."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="linux"
    )
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="linux",
            env={},
        )
    )

    assert outer_timeout > matrix_timeout > inner_timeout
    assert matrix_timeout == pytest.approx(105.0)


def test_non_windows_e2e_plain_delta_writes_stay_in_process() -> None:
    """Non-Windows E2E keeps the faster in-process Delta write default."""
    assert (
        e2e_conftest._resolve_e2e_plain_write_process_isolation(platform="linux")
        is False
    )


def test_pipeline_matrix_timeout_env_override_is_honored() -> None:
    """The matrix-specific timeout remains explicitly overrideable."""
    matrix_timeout = (
        e2e_conftest._resolve_e2e_pipeline_matrix_execution_timeout_seconds(
            platform="win32",
            env={"BIOETL_E2E_PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS": "123.5"},
        )
    )

    assert matrix_timeout == pytest.approx(123.5)
