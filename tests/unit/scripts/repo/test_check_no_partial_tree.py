# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the partial-tree commit guard (#11709)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.engineering.repo import check_no_partial_tree as module


pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo,
        check=True,
    )
    return result.stdout


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "user.email", "test@local")
    for name in (
        "src",
        "docs",
        "scripts",
        "configs",
        "reports",
        "tests",
        "grafana",
        "data",
        ".github",
        "contracts",
    ):
        (tmp_path / name).mkdir()
        (tmp_path / name / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("license", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "full tree")
    return tmp_path


def _commit_partial_tree(repo: Path, message: str) -> str:
    _git(repo, "read-tree", "--empty")
    _git(repo, "add", "reports")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def test_collapsed_tree_rule_accepts_full_restructure_and_rejects_subset() -> None:
    base = frozenset(
        {
            "src",
            "docs",
            "reports",
            "README.md",
            "configs",
            "scripts",
            "tests",
            "grafana",
            "data",
            ".github",
            "LICENSE",
        }
    )
    assert module.is_collapsed_tree(base, base) is False
    assert module.is_collapsed_tree(base, base | {"new_area"}) is False
    assert module.is_collapsed_tree(base, (base - {"src"}) | {"renamed_src"}) is False
    assert module.is_collapsed_tree(base, frozenset({"reports"})) is True
    assert module.is_collapsed_tree(base, frozenset()) is True
    assert module.is_collapsed_tree(frozenset({"a"}), frozenset({"a"})) is False


def test_guard_flags_partial_tree_commit_in_range(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    bad = _commit_partial_tree(repo, "reports-only snapshot")
    assert module.find_collapsing_commits(healthy, bad, repo=repo) == [bad]


def test_rejects_flag_injection_in_revision_tokens(repo: Path) -> None:
    with pytest.raises(SystemExit, match="invalid git revision"):
        module.find_collapsing_commits("--upload-pack=evil", "HEAD", repo=repo)
    with pytest.raises(SystemExit, match="invalid git revision"):
        module.find_collapsing_commits("HEAD", "-c", repo=repo)
    with pytest.raises(SystemExit, match="invalid git repository path"):
        module.validate_repo("-C")


def test_resolve_revision_uses_end_of_options(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []
    real = module._run_git

    def wrapped(cwd: Path, verb: str, *args: str) -> str:
        seen.append([verb, *args])
        return real(cwd, verb, *args)

    monkeypatch.setattr(module, "_run_git", wrapped)
    sha = module.resolve_revision(repo, "HEAD")
    assert module._SHA_RE.fullmatch(sha)
    assert any(row[0] == "rev-parse" and "--end-of-options" in row for row in seen)


def test_guard_passes_clean_range(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "src" / "feature.txt").write_text("feature", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "feature")
    tip = _git(repo, "rev-parse", "HEAD").strip()
    assert module.find_collapsing_commits(healthy, tip, repo=repo) == []
