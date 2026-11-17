"""Navigation seeds carry checked source pointers without historical claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from memory.tooling.navigation_seed import NAVIGATION_SOURCES, build_navigation_seed

pytestmark = pytest.mark.unit


def _sources(root: Path) -> None:
    for _, relative in NAVIGATION_SOURCES:
        source = root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "# Current source\n\nBody: historical version 1.0.\n", encoding="utf-8"
        )


def test_seed_is_deterministic_source_bound_navigation_without_writes(
    tmp_path: Path,
) -> None:
    _sources(tmp_path)
    before = sorted(tmp_path.rglob("*"))
    seed = build_navigation_seed(tmp_path)

    assert seed == build_navigation_seed(tmp_path)
    assert len(seed["entities"]) == len(NAVIGATION_SOURCES)
    assert seed["relations"] == []
    assert "1.0" not in str(seed)
    for entity, (_, relative) in zip(seed["entities"], NAVIGATION_SOURCES, strict=True):
        assert f"Path: {relative}" in entity["observations"]
        digest = hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest()
        assert f"Source SHA256: {digest}" in entity["observations"]
    assert sorted(tmp_path.rglob("*")) == before


def test_seed_fails_closed_on_missing_source(tmp_path: Path) -> None:
    _sources(tmp_path)
    (tmp_path / NAVIGATION_SOURCES[-1][1]).unlink()
    with pytest.raises(FileNotFoundError):
        build_navigation_seed(tmp_path)


def test_seed_fails_closed_on_untitled_source(tmp_path: Path) -> None:
    _sources(tmp_path)
    (tmp_path / "AGENTS.md").write_text("No source heading\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no title"):
        build_navigation_seed(tmp_path)


def test_seed_changes_when_canonical_source_changes(tmp_path: Path) -> None:
    _sources(tmp_path)
    before = build_navigation_seed(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Changed source\n", encoding="utf-8")
    after = build_navigation_seed(tmp_path)
    assert before != after


def test_seed_rejects_source_drift_during_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sources(tmp_path)
    read = Path.read_bytes
    root_reads = 0

    def changing_read(path: Path) -> bytes:
        nonlocal root_reads
        if path == tmp_path / "AGENTS.md":
            root_reads += 1
            if root_reads > 1:
                return b"# Changed during capture\n"
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", changing_read)
    with pytest.raises(RuntimeError, match="changed while building"):
        build_navigation_seed(tmp_path)


def test_seed_rejects_redirected_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sources(tmp_path)
    resolve = Path.resolve

    def redirected(path: Path, strict: bool = False) -> Path:
        if path == tmp_path / "AGENTS.md":
            return tmp_path.parent / "outside.md"
        return resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", redirected)
    with pytest.raises(ValueError, match="escapes its physical root"):
        build_navigation_seed(tmp_path)
