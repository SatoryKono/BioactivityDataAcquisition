from __future__ import annotations

import pytest

import importlib.util
from pathlib import Path


pytestmark = pytest.mark.architecture

_CONFTEST_PATH = Path(__file__).with_name("conftest.py")
_CONFTEST_SPEC = importlib.util.spec_from_file_location(
    "architecture_conftest",
    _CONFTEST_PATH,
)
assert _CONFTEST_SPEC is not None
assert _CONFTEST_SPEC.loader is not None
architecture_conftest = importlib.util.module_from_spec(_CONFTEST_SPEC)
_CONFTEST_SPEC.loader.exec_module(architecture_conftest)


def test_build_text_cache_reads_utf8_files_and_skips_invalid_bytes(
    tmp_path: Path,
) -> None:
    readable = tmp_path / "readable.py"
    readable.write_text("value = 1\n", encoding="utf-8")
    invalid = tmp_path / "invalid.py"
    invalid.write_bytes(b"\xff\xfe\x00")

    cache = architecture_conftest._build_text_cache([readable, invalid])

    assert cache == {readable: "value = 1\n"}


def test_list_markdown_files_via_walk_skips_site_build_tree(tmp_path: Path) -> None:
    """MkDocs ``site/`` trees must not be walked (timeout source on cloud drives)."""
    docs = tmp_path / "docs"
    (docs / "guide").mkdir(parents=True)
    keep = docs / "guide" / "a.md"
    keep.write_text("# a\n", encoding="utf-8")

    site_nested = docs / "site" / "deep" / "nested"
    site_nested.mkdir(parents=True)
    (site_nested / "index.html").write_text("<html></html>", encoding="utf-8")
    # Even a stray .md under site must be ignored because the dir is pruned.
    (site_nested / "noise.md").write_text("# noise\n", encoding="utf-8")

    found = architecture_conftest._list_markdown_files_via_walk(docs)

    assert found == [keep]


def test_list_markdown_files_via_git_returns_none_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# a\n", encoding="utf-8")

    # Isolate Git discovery from any parent repository (e.g. workspace root).
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))

    assert architecture_conftest._list_markdown_files_via_git(docs) is None
    assert architecture_conftest._list_markdown_files(docs) == [docs / "a.md"]


def test_build_ast_cache_skips_syntax_errors(tmp_path: Path) -> None:
    valid = tmp_path / "valid.py"
    invalid = tmp_path / "invalid.py"
    text_cache = {
        valid: "def ok() -> int:\n    return 1\n",
        invalid: "def broken(:\n",
    }

    cache = architecture_conftest._build_ast_cache(text_cache)

    assert list(cache) == [valid]
    assert cache[valid].body


def test_build_yaml_cache_skips_invalid_documents(tmp_path: Path) -> None:
    valid = tmp_path / "valid.yaml"
    invalid = tmp_path / "invalid.yaml"
    text_cache = {
        valid: "name: bioetl\nfeatures:\n  - architecture\n",
        invalid: "name: [unterminated\n",
    }

    cache = architecture_conftest._build_yaml_cache(text_cache)

    assert cache == {valid: {"name": "bioetl", "features": ["architecture"]}}
