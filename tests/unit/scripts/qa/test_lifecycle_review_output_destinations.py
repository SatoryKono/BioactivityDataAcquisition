"""Regression checks for output boundaries found during script lifecycle review."""

from __future__ import annotations

import importlib
import json
import os
import stat
from pathlib import Path

import pytest

from scripts.data_quality import run_silver_gold_filter_parity as parity
from scripts.engineering.common import repo_paths
from scripts.engineering.common import report_outputs
from scripts.engineering.common.report_outputs import write_report_outputs

pytestmark = pytest.mark.unit


def test_report_outputs_invalid_markdown_parent_preserves_json(tmp_path: Path) -> None:
    json_out = tmp_path / "report.json"
    json_out.write_text("old json", encoding="utf-8")
    blocked = tmp_path / "blocked"
    blocked.write_text("ordinary file", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_report_outputs(
            {"new": True},
            json_out=json_out,
            md_out=blocked / "report.md",
            markdown="new markdown",
            root=tmp_path,
        )
    assert json_out.read_text(encoding="utf-8") == "old json"
    assert blocked.read_text(encoding="utf-8") == "ordinary file"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission mode contract")
def test_report_outputs_preserve_existing_permissions(tmp_path: Path) -> None:
    json_out, md_out = tmp_path / "report.json", tmp_path / "report.md"
    for path, mode in ((json_out, 0o640), (md_out, 0o644)):
        path.write_text("old", encoding="utf-8")
        path.chmod(mode)
    write_report_outputs(
        {"new": True},
        json_out=json_out,
        md_out=md_out,
        markdown="new",
        root=tmp_path,
    )
    assert stat.S_IMODE(json_out.stat().st_mode) == 0o640
    assert stat.S_IMODE(md_out.stat().st_mode) == 0o644


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory symlink substitution")
def test_report_outputs_reject_substitution_before_confined_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    parent = root / "reports"
    parent.mkdir(parents=True)
    outside.mkdir()
    protected = outside / "report.json"
    protected.write_text("protected", encoding="utf-8")
    writer = report_outputs.write_text_confined

    def substitute(
        path: Path, data: str, *, root: Path, allow_external_absolute: bool
    ) -> Path:
        parent.rename(root / "original-reports")
        parent.symlink_to(outside, target_is_directory=True)
        return writer(
            path, data, root=root, allow_external_absolute=allow_external_absolute
        )

    monkeypatch.setattr(report_outputs, "write_text_confined", substitute)
    with pytest.raises(ValueError, match="refusing path outside"):
        write_report_outputs(
            {"new": True},
            json_out=Path("reports/report.json"),
            md_out=Path("reports/report.md"),
            markdown="new",
            root=root,
        )
    assert protected.read_text(encoding="utf-8") == "protected"
    assert not (outside / "report.md").exists()


def test_report_outputs_reject_second_relative_escape_before_publication(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(ValueError, match="refusing path outside"):
        write_report_outputs(
            {"status": "pass"},
            json_out=Path("json/report.json"),
            md_out=Path("../escape/report.md"),
            markdown="Report\n",
            root=root,
        )

    assert not (root / "json").exists()
    assert not (tmp_path / "escape").exists()


def test_report_outputs_preserve_explicit_external_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(repo_paths, "REPO_ROOT", root)
    json_out = tmp_path / "external-json/report.json"
    md_out = tmp_path / "external-markdown/report.md"

    published = write_report_outputs(
        {"value": "текст"},
        json_out=json_out,
        md_out=md_out,
        markdown="Report\n",
        root=root,
    )

    assert published == (json_out, md_out)
    assert json.loads(json_out.read_text(encoding="utf-8")) == {"value": "текст"}
    assert md_out.read_text(encoding="utf-8") == "Report\n"


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
