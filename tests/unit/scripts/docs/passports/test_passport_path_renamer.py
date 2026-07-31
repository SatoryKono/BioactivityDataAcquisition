"""Tests for the passport Markdown path migration."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.docs.passports.rename_underscore_to_hyphen import main

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)


def test_migration_dry_run_apply_and_check_are_idempotent(
    tmp_path: Path,
) -> None:
    pipeline_legacy_name = "chembl" + "_activity.md"
    workflow_legacy_name = "publication" + "_provider_pack.md"
    pipeline = (
        tmp_path
        / "docs/04-reference/passports/pipelines"
        / pipeline_legacy_name
    )
    workflow = (
        tmp_path
        / "docs/04-reference/passports/workflows"
        / workflow_legacy_name
    )
    _write(pipeline, "# pipeline\n")
    _write(workflow, "# workflow\n")
    index = tmp_path / "docs/04-reference/passports/index.md"
    _write(
        index,
        f"[pipeline](pipelines/{pipeline_legacy_name})\n"
        f"[workflow](workflows/{workflow_legacy_name})\n",
    )
    mkdocs = tmp_path / "mkdocs.yml"
    _write(
        mkdocs,
        "nav:\n"
        "  - Pipeline: docs/04-reference/passports/pipelines/"
        f"{pipeline_legacy_name}\n",
    )
    _init_repo(tmp_path)

    assert main(["--root", str(tmp_path)]) == 0
    assert pipeline.exists()
    assert main(["--root", str(tmp_path), "--check"]) == 1

    assert main(["--root", str(tmp_path), "--apply"]) == 0
    assert not pipeline.exists()
    assert not workflow.exists()
    assert pipeline.with_name("chembl-activity.md").is_file()
    assert workflow.with_name("publication-provider-pack.md").is_file()
    assert "pipelines/chembl-activity.md" in index.read_text(encoding="utf-8")
    assert "workflows/publication-provider-pack.md" in index.read_text(
        encoding="utf-8"
    )
    assert "pipelines/chembl-activity.md" in mkdocs.read_text(encoding="utf-8")
    assert main(["--root", str(tmp_path), "--check"]) == 0


def test_migration_refuses_to_overwrite_existing_target(tmp_path: Path) -> None:
    directory = tmp_path / "docs/04-reference/passports/pipelines"
    _write(directory / ("chembl" + "_activity.md"), "old\n")
    _write(directory / "chembl-activity.md", "new\n")
    _init_repo(tmp_path)

    with pytest.raises(FileExistsError, match="target exists"):
        main(["--root", str(tmp_path), "--apply"])
