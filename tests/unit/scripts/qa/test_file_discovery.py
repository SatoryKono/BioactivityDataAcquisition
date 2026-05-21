"""Unit tests for shared QA file-discovery helpers."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.qa.file_discovery import discover_files


def test_discover_files_returns_sorted_relative_matches(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "alpha.py").write_text("", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "beta.py").write_text("", encoding="utf-8")
    (nested / "skip.txt").write_text("", encoding="utf-8")

    discovered = discover_files(str(root), ".py")

    assert discovered == ("alpha.py", "nested/beta.py")


def test_discover_files_prunes_known_cache_and_fixture_roots(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    fixture_dir = root / "tests" / "fixtures" / "vcr"
    cache_dir = root / ".venv"
    good_dir = root / "src"
    fixture_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)
    good_dir.mkdir(parents=True)

    (fixture_dir / "fixture.py").write_text("", encoding="utf-8")
    (cache_dir / "cached.py").write_text("", encoding="utf-8")
    (good_dir / "live.py").write_text("", encoding="utf-8")

    discovered = discover_files(str(root), ".py")

    assert discovered == ("src/live.py",)


def test_discover_files_supports_filename_prefix_filter(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "_private.py").write_text("", encoding="utf-8")
    (root / "public.py").write_text("", encoding="utf-8")

    discovered = discover_files(str(root), ".py", "_")

    assert discovered == ("_private.py",)
