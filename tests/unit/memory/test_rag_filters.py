"""Tests for deterministic RAG source filtering."""

from __future__ import annotations

import pytest

from subprocess import CompletedProcess
from pathlib import Path

from memory.rag.filters import _candidate_source_paths, _safe_source_path


pytestmark = pytest.mark.unit


def test_candidate_source_paths_avoids_path_is_file(
    monkeypatch, tmp_path: Path
) -> None:
    docs_root = tmp_path / "docs" / "00-project"
    docs_root.mkdir(parents=True)
    (docs_root / "b.md").write_text("# B\n", encoding="utf-8")
    nested = docs_root / "nested"
    nested.mkdir()
    (nested / "a.md").write_text("# A\n", encoding="utf-8")
    (nested / "ignore.txt").write_text("ignore\n", encoding="utf-8")

    def _explode(self):  # pragma: no cover - regression guard
        raise AssertionError("is_file() should not be called for candidate discovery")

    monkeypatch.setattr(Path, "is_file", _explode)

    candidates = _candidate_source_paths(
        root=tmp_path,
        source_id="active_docs",
        base=Path("docs/00-project"),
    )

    assert [path.as_posix() for path in candidates] == [
        "docs/00-project/b.md",
        "docs/00-project/nested/a.md",
    ]


def test_candidate_source_paths_uses_git_tracked_and_untracked_files(
    monkeypatch, tmp_path: Path
) -> None:
    docs_root = tmp_path / "docs" / "00-project"
    docs_root.mkdir(parents=True)
    (docs_root / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (docs_root / "untracked.md").write_text("# New\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    calls: list[tuple[str, ...]] = []

    def _fake_run(*args, **kwargs):
        calls.append(tuple(args[0]))
        return CompletedProcess(
            args[0],
            0,
            stdout=(
                "docs/00-project/alpha.md\n"
                "docs/00-project/beta.txt\n"
                "docs/00-project/untracked.md\n"
            ),
            stderr="",
        )

    def _explode(*args, **kwargs):  # pragma: no cover - regression guard
        raise AssertionError("os.walk() fallback should not be used when git is ready")

    monkeypatch.setattr("memory.rag.filters.subprocess.run", _fake_run)
    monkeypatch.setattr("memory.rag.filters.os.walk", _explode)

    candidates = _candidate_source_paths(
        root=tmp_path,
        source_id="active_docs",
        base=Path("docs/00-project"),
    )

    assert calls == [
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "docs/00-project",
        )
    ]
    assert [path.as_posix() for path in candidates] == [
        "docs/00-project/alpha.md",
        "docs/00-project/untracked.md",
    ]


def test_candidate_sources_exclude_untracked_symlink_outside_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    docs_root = tmp_path / "docs/00-project"
    docs_root.mkdir(parents=True)
    (docs_root / "safe.md").write_text("# Safe\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-secret.md"
    outside.write_text("outside repository\n", encoding="utf-8")
    link = docs_root / "linked.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    monkeypatch.setattr(
        "memory.rag.filters.subprocess.run",
        lambda args, **_kwargs: CompletedProcess(
            args,
            0,
            stdout="docs/00-project/linked.md\ndocs/00-project/safe.md\n",
            stderr="",
        ),
    )
    expected = [Path("docs/00-project/safe.md")]
    assert (
        _candidate_source_paths(
            root=tmp_path, source_id="active_docs", base=Path("docs/00-project")
        )
        == expected
    )
    git_dir.rmdir()
    assert (
        _candidate_source_paths(
            root=tmp_path, source_id="active_docs", base=Path("docs/00-project")
        )
        == expected
    )


def test_candidate_source_boundary_rejects_outside_file(tmp_path: Path) -> None:
    inside = tmp_path / "inside.md"
    inside.write_text("inside\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("outside\n", encoding="utf-8")

    assert _safe_source_path(inside, tmp_path.resolve())
    assert not _safe_source_path(outside, tmp_path.resolve())


def test_git_empty_source_set_does_not_fall_back_to_ignored_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_root = tmp_path / "docs/00-project"
    docs_root.mkdir(parents=True)
    (docs_root / "ignored.md").write_text("# Ignored\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        "memory.rag.filters.subprocess.run",
        lambda args, **_kwargs: CompletedProcess(args, 0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        "memory.rag.filters.os.walk",
        lambda *_args, **_kwargs: pytest.fail(
            "Git empty set must not scan ignored files"
        ),
    )

    assert (
        _candidate_source_paths(
            root=tmp_path, source_id="active_docs", base=Path("docs/00-project")
        )
        == []
    )


def test_candidate_source_paths_supports_single_file_sources(tmp_path: Path) -> None:
    wiki_path = tmp_path / ".devin" / "wiki.json"
    wiki_path.parent.mkdir(parents=True)
    wiki_path.write_text('{"pages": []}\n', encoding="utf-8")

    candidates = _candidate_source_paths(
        root=tmp_path,
        source_id="devin_wiki",
        base=Path(".devin/wiki.json"),
    )

    assert [path.as_posix() for path in candidates] == [".devin/wiki.json"]
