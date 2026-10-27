import json
from pathlib import Path
from unittest import mock

import pytest

from scripts.engineering.ci.check_mypy_diagnostic_ratchet import main, _parse_mypy_output

pytestmark = pytest.mark.unit

def test_parse_mypy_output(tmp_path: Path) -> None:
    log = tmp_path / 'mypy.log'
    log.touch()
    # Test fail closed
    with pytest.raises(FileNotFoundError):
        _parse_mypy_output(tmp_path / 'nonexistent.log')

def test_parse_mypy_output_valid(tmp_path: Path) -> None:
    log = tmp_path / "mypy.log"
    log.write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n"
        "src/bioetl/a.py:12: error: Incompatible return type [return-value]\n"
        "src/bioetl/b.py:5: error: Missing type arg [type-arg]\n",
        encoding="utf-8"
    )
    diagnostics = _parse_mypy_output(log)
    assert diagnostics["src/bioetl/a.py"]["Incompatible return type"]["return-value"] == 2
    assert diagnostics["src/bioetl/b.py"]["Missing type arg"]["type-arg"] == 1

@mock.patch("scripts.engineering.ci.check_mypy_diagnostic_ratchet.Path.resolve")
def test_ratchet_pass(mock_resolve, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "reports").mkdir()
    (repo_root / "configs" / "quality").mkdir(parents=True)

    mock_resolve.return_value = repo_root / "scripts" / "engineering" / "ci" / "check_mypy_diagnostic_ratchet.py"

    baseline = {
        "src/bioetl/a.py": {
            "Incompatible return type": {
                "return-value": 2
            }
        }
    }
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )

    (repo_root / "reports" / "mypy_strict.log").write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n",
        encoding="utf-8"
    )

    assert main() == 0
    assert "Mypy diagnostic ratchet passed" in capsys.readouterr().out

@mock.patch("scripts.engineering.ci.check_mypy_diagnostic_ratchet.Path.resolve")
def test_ratchet_fail_new_error(mock_resolve, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "reports").mkdir()
    (repo_root / "configs" / "quality").mkdir(parents=True)

    mock_resolve.return_value = repo_root / "scripts" / "engineering" / "ci" / "check_mypy_diagnostic_ratchet.py"

    baseline = {
        "src/bioetl/a.py": {
            "Incompatible return type": {
                "return-value": 1
            }
        }
    }
    (repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )

    (repo_root / "reports" / "mypy_strict.log").write_text(
        "src/bioetl/a.py:10: error: Incompatible return type [return-value]\n"
        "src/bioetl/a.py:15: error: Incompatible return type [return-value]\n",
        encoding="utf-8"
    )

    assert main() == 1
    assert "Mypy diagnostic ratchet failed" in capsys.readouterr().out
