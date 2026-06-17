"""Unit tests for Windows-aware xdist limits in the dev test runner."""

from __future__ import annotations

import pytest

from scripts.engineering.dev import run_tests


pytestmark = pytest.mark.unit


def test_default_parallel_workers_are_capped_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_tests.os, "name", "nt")
    monkeypatch.delenv("BIOETL_PYTEST_PARALLEL_WORKERS", raising=False)
    monkeypatch.delenv("BIOETL_PYTEST_WINDOWS_XDIST_WORKERS", raising=False)

    assert run_tests._default_parallel_workers() == "2"


def test_default_parallel_workers_respect_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_tests.os, "name", "nt")
    monkeypatch.setenv("BIOETL_PYTEST_PARALLEL_WORKERS", "5")

    assert run_tests._default_parallel_workers() == "5"


def test_parallel_args_use_auto_outside_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_tests.os, "name", "posix")
    monkeypatch.delenv("BIOETL_PYTEST_PARALLEL_WORKERS", raising=False)
    monkeypatch.delenv("BIOETL_PYTEST_WINDOWS_XDIST_WORKERS", raising=False)

    assert run_tests._parallel_args() == ["tests/", "-n", "auto", "-q"]


def test_changed_fallback_uses_windows_worker_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_tests.os, "name", "nt")
    monkeypatch.setattr(run_tests, "_git_changed_python_files", lambda *_args: [])

    recorded: dict[str, object] = {}

    def _fake_run_pytest(
        label: str,
        pytest_args: list[str],
        extra: list[str],
        env_overrides: dict[str, str] | None = None,
    ) -> int:
        recorded["label"] = label
        recorded["pytest_args"] = pytest_args
        recorded["extra"] = extra
        recorded["env_overrides"] = env_overrides
        return 0

    monkeypatch.setattr(run_tests, "_run_pytest", _fake_run_pytest)

    assert run_tests._run_changed([]) == 0
    assert recorded["label"] == "Changed fallback: unit tests"
    assert recorded["pytest_args"] == [
        "tests/unit/",
        "-m",
        "not slow and not serial",
        "-n",
        "2",
        "--dist",
        "loadscope",
        "-q",
        "--tb=short",
    ]
