"""Live provider contracts must fail closed on HTTP 5xx, never skip (#11772).

Skip stays legal only for unreachable endpoints (transport/timeout errors)
and HTTP 429 rate-limiting. A received 5xx response is provider evidence and
must fail the test via ``pytest.fail`` so outages cannot present as
skipped-green.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIVE_CONTRACT_FILES = (
    "tests/contract/test_chembl_contract.py",
    "tests/contract/test_crossref_contract.py",
    "tests/contract/test_openalex_contract.py",
    "tests/contract/test_pubchem_contract.py",
    "tests/contract/test_pubmed_contract.py",
    "tests/contract/test_uniprot_contract.py",
)
_SERVER_ERROR_GUARD_TOKENS = ("500", "5xx", "5XX", "SERVER_ERROR")

pytestmark = pytest.mark.architecture


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _qualified_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return None


def _skip_calls_under_server_error_guard(source: str) -> list[int]:
    """Line numbers of ``pytest.skip`` calls guarded by a 5xx branch."""
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _qualified_name(node.func) != "pytest.skip":
            continue
        current = node
        while current in parents:
            current = parents[current]
            if isinstance(current, ast.If):
                guard = ast.unparse(current.test)
                if any(token in guard for token in _SERVER_ERROR_GUARD_TOKENS):
                    offenders.append(node.lineno)
                    break
    return offenders


@pytest.mark.parametrize("relative_path", LIVE_CONTRACT_FILES)
def test_live_contracts_never_skip_on_server_error(relative_path: str) -> None:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    assert _skip_calls_under_server_error_guard(source) == [], (
        f"{relative_path} skips under a 5xx branch; fail closed with pytest.fail"
    )


@pytest.mark.parametrize("relative_path", LIVE_CONTRACT_FILES)
def test_live_contracts_fail_closed_on_server_error(relative_path: str) -> None:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    assert "pytest.fail(" in source, (
        f"{relative_path} must fail closed on received HTTP 5xx via pytest.fail"
    )
