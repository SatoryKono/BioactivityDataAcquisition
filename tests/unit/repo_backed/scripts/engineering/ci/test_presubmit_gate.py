from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from scripts.engineering.ci.presubmit_gate import main


def test_presubmit_dirty_diffs(monkeypatch, tmp_path):
    """Test that presubmit exits with 1 when ruff/mypy checks fail due to dirty diffs."""
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.resolve_ref", lambda x: "dummy_sha")
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.collect_changed_files", lambda b, h: ["src/bioetl/some_file.py"])

    mock_run_ruff = MagicMock(return_value=False)
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.run_ruff", mock_run_ruff)

    with pytest.raises(SystemExit) as excinfo:
        main(["--base", "origin/main", "--head", "HEAD"])

    assert excinfo.value.code == 1
    mock_run_ruff.assert_called_once()


def test_presubmit_unformatted_paths(monkeypatch, tmp_path):
    """Test that presubmit fails when unformatted files are present in scripts/ etc."""
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.resolve_ref", lambda x: "dummy_sha")
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.collect_changed_files", lambda b, h: ["scripts/some_script.py"])

    # simulate ruff format failure
    mock_run_ruff = MagicMock(return_value=False)
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.run_ruff", mock_run_ruff)

    with pytest.raises(SystemExit) as excinfo:
        main(["--base", "origin/main", "--head", "HEAD"])

    assert excinfo.value.code == 1
    mock_run_ruff.assert_called_once()


def test_presubmit_broken_refs(monkeypatch):
    """Test that presubmit fails when broken git refs are provided."""
    def mock_resolve_ref(ref):
        sys.exit(1)

    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.resolve_ref", mock_resolve_ref)

    with pytest.raises(SystemExit) as excinfo:
        main(["--base", "invalid_ref", "--head", "HEAD"])

    assert excinfo.value.code == 1


def test_presubmit_python_type_error(monkeypatch):
    """Test that presubmit fails when strict mypy detects type errors."""
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.resolve_ref", lambda x: "dummy_sha")
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.collect_changed_files", lambda b, h: ["src/bioetl/domain/something.py"])

    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.run_ruff", lambda: True)

    # simulate mypy failure
    mock_run_mypy = MagicMock(return_value=False)
    monkeypatch.setattr("scripts.engineering.ci.presubmit_gate.run_mypy", mock_run_mypy)

    with pytest.raises(SystemExit) as excinfo:
        main(["--base", "origin/main", "--head", "HEAD"])

    assert excinfo.value.code == 1
    mock_run_mypy.assert_called_once()
