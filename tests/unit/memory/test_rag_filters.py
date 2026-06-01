"""Tests for deterministic RAG source filtering."""

from __future__ import annotations

import pytest

from subprocess import CompletedProcess
from pathlib import Path

from memory.rag.filters import _candidate_source_paths


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


def test_candidate_source_paths_prefers_git_tracked_files(
    monkeypatch, tmp_path: Path
) -> None:
    docs_root = tmp_path / "docs" / "00-project"
    docs_root.mkdir(parents=True)
    (tmp_path / ".git").mkdir()

    calls: list[tuple[str, ...]] = []

    def _fake_run(*args, **kwargs):
        calls.append(tuple(args[0]))
        return CompletedProcess(
            args[0],
            0,
            stdout="docs/00-project/alpha.md\ndocs/00-project/beta.txt\n",
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

    assert calls == [("git", "ls-files", "--", "docs/00-project")]
    assert [path.as_posix() for path in candidates] == ["docs/00-project/alpha.md"]


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
