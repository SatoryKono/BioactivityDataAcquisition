"""Regression tests for schema artifact generation helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.repo_backed


def _load_module() -> ModuleType:
    """Load the schema artifact generator script as a testable module."""
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "schema"
        / "generate_schema_artifacts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_generate_schema_artifacts_module",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_check_mode_does_not_invoke_subprocess_generation(monkeypatch) -> None:
    """Check mode must compare snapshots without rewriting generated contracts."""
    module = _load_module()

    called = False

    def _fail_subprocess(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess.run must not be called in check mode")

    monkeypatch.setattr(module.subprocess, "run", _fail_subprocess)
    monkeypatch.setattr(
        module,
        "_snapshot_generated_contracts",
        lambda: {"docs/04-reference/contracts/gold/example_v1.0.json": "{}\n"},
    )
    monkeypatch.setattr(
        module,
        "_expected_generated_contracts_snapshot",
        lambda: {"docs/04-reference/contracts/gold/example_v1.0.json": "{}\n"},
    )

    assert module._run_gold_contract_generation(check=True) is False
    assert called is False


def test_check_mode_reports_stale_snapshot_without_writing(monkeypatch) -> None:
    """Check mode should still report drift when current and expected differ."""
    module = _load_module()

    called = False

    def _fail_subprocess(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess.run must not be called in check mode")

    monkeypatch.setattr(module.subprocess, "run", _fail_subprocess)
    monkeypatch.setattr(
        module,
        "_snapshot_generated_contracts",
        lambda: {"docs/04-reference/contracts/gold/example_v1.0.json": "{}\n"},
    )
    monkeypatch.setattr(
        module,
        "_expected_generated_contracts_snapshot",
        lambda: {"docs/04-reference/contracts/gold/example_v1.0.json": '{"x":1}\n'},
    )

    assert module._run_gold_contract_generation(check=True) is True
    assert called is False
