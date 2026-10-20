"""Single governed PMCID normalizer (#12027)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.domain.normalization import __all__ as normalization_exports
from bioetl.domain.normalization.join_keys import JOIN_KEY_NORMALIZATION_POLICIES

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "bioetl"
_LEGACY_NAME = "normalize_pmc_id"
_GOVERNED_NAME = "normalize_pmcid_reference_id"


def _function_names(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def test_src_has_one_pmcid_normalizer() -> None:
    governed = [
        path
        for path in SRC.rglob("*.py")
        if _GOVERNED_NAME in _function_names(path.read_text(encoding="utf-8"))
    ]
    legacy = [
        path
        for path in SRC.rglob("*.py")
        if _LEGACY_NAME in _function_names(path.read_text(encoding="utf-8"))
    ]
    assert [path.relative_to(ROOT).as_posix() for path in governed] == [
        "src/bioetl/domain/normalization/_reference_id_normalizers.py"
    ]
    assert legacy == []
    assert _LEGACY_NAME not in normalization_exports


def test_synthetic_legacy_pmcid_def_is_detected() -> None:
    sample = (
        "def normalize_pmc_id(value: str | None) -> str | None:\n    return value\n"
    )
    assert _LEGACY_NAME in _function_names(sample)


def test_pmc_join_keys_keep_canonical_case() -> None:
    for key in ("pmc_id", "pmcid"):
        policy = JOIN_KEY_NORMALIZATION_POLICIES[key]
        assert policy.lowercase is False
        assert policy.domain_canonicalizer is not None
