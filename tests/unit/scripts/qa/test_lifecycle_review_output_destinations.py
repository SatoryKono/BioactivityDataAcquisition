"""Regression checks for output boundaries found during script lifecycle review."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from scripts.data_quality import run_silver_gold_filter_parity as parity
from scripts.engineering.common import repo_paths

pytestmark = pytest.mark.unit


def test_parity_rejects_relative_escape_before_creating_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(repo_paths, "REPO_ROOT", repo)
    monkeypatch.chdir(repo)

    with pytest.raises(ValueError, match="refusing path outside"):
        parity._write_json(Path("../escape/report.json"), {"status": "pass"})

    assert not (tmp_path / "escape").exists()


def test_parity_resolves_relative_output_before_creating_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    foreign = tmp_path / "foreign"
    repo.mkdir()
    foreign.mkdir()
    monkeypatch.setattr(repo_paths, "REPO_ROOT", repo)
    monkeypatch.chdir(foreign)

    parity._write_json(Path("reports/result.json"), {"status": "pass"})

    assert json.loads((repo / "reports/result.json").read_text()) == {"status": "pass"}
    assert not (foreign / "reports").exists()


def test_parity_preserves_explicit_absolute_external_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(repo_paths, "REPO_ROOT", repo)
    output = tmp_path / "external/result.json"

    parity._write_json(output, {"status": "pass"})

    assert json.loads(output.read_text()) == {"status": "pass"}


@pytest.mark.parametrize(
    "module_name",
    [
        "report_architecture_suite_burndown",
        "report_vcr_corpus_budget",
        "report_weak_assert_inventory",
    ],
)
def test_report_cli_creates_distinct_markdown_destination(
    module_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"scripts.engineering.qa.{module_name}")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    source = tmp_path / "tests/architecture/test_example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def test_example():\n    assert True\n", encoding="utf-8")
    args = ["--json-out", "json/report.json", "--md-out", "markdown/report.md"]
    if module_name == "report_architecture_suite_burndown":
        # Keep discovery independent of the real repository index; scan real text.
        monkeypatch.setattr(module, "tracked_files", lambda *args: [source])
    elif module_name == "report_vcr_corpus_budget":
        policy = tmp_path / "policy.yaml"
        policy.write_text("corpus_size_budget: {}\n", encoding="utf-8")
        args.extend(["--policy", str(policy), "--vcr-root", str(tmp_path / "vcr")])

    assert module.main(args) == 0
    assert isinstance(json.loads((tmp_path / "json/report.json").read_text()), dict)
    assert (tmp_path / "markdown/report.md").read_text(encoding="utf-8").strip()
