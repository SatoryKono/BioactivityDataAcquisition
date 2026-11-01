"""Engineering discovery stays Git-aware without contaminating installed runtime."""

from __future__ import annotations

import subprocess

import pytest

from scripts.engineering.qa import report_observability_metric_inventory as inventory
from bioetl.infrastructure.observability import metric_inventory_assembly as assembly
from bioetl.infrastructure.observability import (
    metric_inventory_candidates as candidates,
)

pytestmark = pytest.mark.unit


def test_collection_excludes_gitignored_docs_and_restores_runtime_callbacks(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    docs = tmp_path / "docs/03-guides"
    docs.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("docs/03-guides/local-draft.md\n")
    (docs / "tracked.md").write_text("bioetl_errors_total\n")
    (docs / "tracked_я.md").write_text("# UTF-8 filename boundary\n", encoding="utf-8")
    (docs / "local-draft.md").write_text("bioetl_review_ignored_total\n")
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "add",
            ".gitignore",
            "docs/03-guides/tracked.md",
            "docs/03-guides/tracked_я.md",
        ],
        check=True,
    )
    before = (
        assembly._iter_text_files,
        assembly._scan_canonical_metric_mentions,
        candidates._iter_text_files,
    )
    report = inventory.collect_metric_inventory(tmp_path)
    assert report["docs_mentions"]["bioetl_errors_total"] == [
        "docs/03-guides/tracked.md"
    ]
    assert "bioetl_review_ignored_total" not in report["docs_mentions"]
    assert "bioetl_review_ignored_total" not in report["documented_without_registry"]
    from bioetl.infrastructure.observability import (
        metric_inventory_discovery as discovery,
    )

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GIT_DIR", str(tmp_path / "foreign-git-dir"))
        patch.setenv("GIT_WORK_TREE", str(tmp_path / "foreign-worktree"))
        patch.setenv("GIT_INDEX_FILE", str(tmp_path / "foreign-index"))
        assert discovery._iter_text_files(docs) == [
            docs / "tracked.md",
            docs / "tracked_я.md",
        ]
    assert (
        assembly._iter_text_files,
        assembly._scan_canonical_metric_mentions,
        candidates._iter_text_files,
    ) == before


def test_callback_restoration_survives_collection_failure(tmp_path, monkeypatch):
    before = assembly._iter_text_files

    def fail(*args, **kwargs):
        assert assembly._iter_text_files is not before
        raise RuntimeError("collection failed")

    monkeypatch.setattr(inventory, "_collect_metric_inventory_impl", fail)
    with pytest.raises(RuntimeError, match="collection failed"):
        inventory.collect_metric_inventory(tmp_path)
    assert assembly._iter_text_files is before


def test_plain_installed_root_does_not_execute_git(tmp_path, monkeypatch):
    from bioetl.infrastructure.observability import (
        metric_inventory_discovery as discovery,
    )

    (tmp_path / "input.md").write_text("bioetl_errors_total")

    def forbidden(*args, **kwargs):
        pytest.fail("Installed roots must not require a Git executable")

    from bioetl.infrastructure.provenance import code_revision

    monkeypatch.setattr(code_revision.subprocess, "run", forbidden)
    assert discovery._iter_text_files(tmp_path) == [tmp_path / "input.md"]


def test_checkout_without_git_executable_still_scans_explicit_root(
    tmp_path, monkeypatch
):
    from bioetl.infrastructure.observability import (
        metric_inventory_discovery as discovery,
    )

    (tmp_path / ".git").mkdir()
    (tmp_path / "input.md").write_text("bioetl_errors_total")

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("git unavailable")

    from bioetl.infrastructure.provenance import code_revision

    monkeypatch.setattr(code_revision.subprocess, "run", unavailable)
    assert discovery._iter_text_files(tmp_path) == [tmp_path / "input.md"]
