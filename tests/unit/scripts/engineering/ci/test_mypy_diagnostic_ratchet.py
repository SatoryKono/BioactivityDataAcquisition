from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from scripts.engineering.ci import _parse_mypy_output, run_mypy_diagnostic_ratchet

pytestmark = pytest.mark.unit


def test_parse_mypy_output_missing_log_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _parse_mypy_output(tmp_path / "nonexistent.log")


def test_parse_mypy_output_valid(tmp_path: Path) -> None:
    log = tmp_path / "mypy.log"
    log.write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n"
        "src/bioetl/a.py:12:4: error: Incompatible return type [return-value]\n"
        "src/bioetl/b.py:5: error: Missing type arg [type-arg]\n"
        "src/bioetl/c.py:1: note: ignored note\n",
        encoding="utf-8",
    )
    diagnostics = _parse_mypy_output(log)
    assert (
        diagnostics["src/bioetl/a.py"]["Incompatible return type"]["return-value"] == 2
    )
    assert diagnostics["src/bioetl/b.py"]["Missing type arg"]["type-arg"] == 1
    assert "src/bioetl/c.py" not in diagnostics


def test_parse_mypy_output_without_line_number(tmp_path: Path) -> None:
    log = tmp_path / "mypy.log"
    log.write_text(
        'dir/a.py: error: Duplicate module named "a" [no-redef]\n',
        encoding="utf-8",
    )
    diagnostics = _parse_mypy_output(log)
    assert diagnostics["dir/a.py"]['Duplicate module named "a"']["no-redef"] == 1


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "reports").mkdir(parents=True)
    (repo_root / "configs" / "quality").mkdir(parents=True)
    return repo_root


def _patch_repo(mock_resolve: mock.Mock, repo_root: Path) -> None:
    mock_resolve.return_value = (
        repo_root / "scripts" / "engineering" / "ci" / "__init__.py"
    )


def _write_exit_code(repo_root: Path, code: int) -> None:
    (repo_root / "reports" / "mypy_strict.exit_code").write_text(
        f"{code}\n", encoding="utf-8"
    )


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_pass(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)

    baseline = {"src/bioetl/a.py": {"Incompatible return type": {"return-value": 2}}}
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    (repo_root / "reports" / "mypy_strict.log").write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n",
        encoding="utf-8",
    )
    _write_exit_code(repo_root, 1)

    assert run_mypy_diagnostic_ratchet() == 0
    assert "Mypy diagnostic ratchet passed" in capsys.readouterr().out


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_fail_new_error(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)

    baseline = {"src/bioetl/a.py": {"Incompatible return type": {"return-value": 1}}}
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    (repo_root / "reports" / "mypy_strict.log").write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n"
        "src/bioetl/a.py:15: error: Incompatible return type [return-value]\n",
        encoding="utf-8",
    )
    _write_exit_code(repo_root, 1)

    assert run_mypy_diagnostic_ratchet() == 1
    assert "Mypy diagnostic ratchet failed" in capsys.readouterr().out


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_missing_log_fails_closed(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        "{}", encoding="utf-8"
    )

    assert run_mypy_diagnostic_ratchet() == 1
    assert "mypy log file not found" in capsys.readouterr().out


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_invalid_baseline_json(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        "{", encoding="utf-8"
    )
    (repo_root / "reports" / "mypy_strict.log").write_text("", encoding="utf-8")
    _write_exit_code(repo_root, 0)

    assert run_mypy_diagnostic_ratchet() == 1
    assert "Invalid JSON" in capsys.readouterr().out


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_event_only_log_with_failing_exit_code(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        "{}", encoding="utf-8"
    )
    (repo_root / "reports" / "mypy_strict.log").write_text(
        "Event: pull_request\n", encoding="utf-8"
    )
    _write_exit_code(repo_root, 1)

    assert run_mypy_diagnostic_ratchet() == 1
    assert "without recognized diagnostics" in capsys.readouterr().out


@mock.patch("scripts.engineering.ci.Path.resolve")
def test_ratchet_missing_exit_code_fails_closed(
    mock_resolve: mock.Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo_root(tmp_path)
    _patch_repo(mock_resolve, repo_root)
    (repo_root / "reports" / "mypy_strict.log").write_text("", encoding="utf-8")

    assert run_mypy_diagnostic_ratchet() == 1
    assert "exit code file not found" in capsys.readouterr().out
