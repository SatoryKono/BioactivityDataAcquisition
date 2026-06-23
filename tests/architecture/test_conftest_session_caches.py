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
