"""Application and domain policy functions take explicit data."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_ROOT = _REPO_ROOT / "src" / "bioetl"
_BANNED_CALLS = (
    "current_protein_class_target_type_mapping(",
    "publication_controlled_vocabulary_values(",
)
_DEFINITION_FILES = {
    "domain/mapping/protein_class_target_type.py",
    "domain/mapping/publication_controlled_vocabulary.py",
    "domain/mapping/publication_type_classification.py",
}
_KEYWORD_DATA_FUNCTIONS = {
    "classify_publication_type",
    "build_publication_type_classification_payload",
    "classification_payload",
    "normalize_publication_classification_field",
}
_POSITIONAL_DATA_FUNCTIONS = {"publication_classification_values"}


def _imported_policy_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if not node.module.endswith(
            (
                "publication_type_classification",
                "publication_transformer_records",
            )
        ):
            continue
        for alias in node.names:
            names.add(alias.asname or alias.name)
    return names


def _missing_classification_data(tree: ast.AST) -> list[str]:
    imported = _imported_policy_names(tree)
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in imported:
            continue
        if name in _KEYWORD_DATA_FUNCTIONS and not any(
            keyword.arg == "data" for keyword in node.keywords
        ):
            missing.append(f"{name} missing data=")
        if name in _POSITIONAL_DATA_FUNCTIONS and not (
            any(keyword.arg == "data" for keyword in node.keywords)
            or len(node.args) >= 2
        ):
            missing.append(f"{name} missing data")
    return missing


@pytest.mark.architecture
def test_application_and_domain_do_not_call_ambient_policy_registries() -> None:
    hits: list[str] = []
    for path in _SCAN_ROOT.rglob("*.py"):
        relative = path.relative_to(_SCAN_ROOT).as_posix()
        if relative.startswith("composition/") or relative in _DEFINITION_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for token in _BANNED_CALLS:
            if token in text:
                hits.append(f"{relative}: {token}")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            hits.append(f"{relative}: syntax error {exc}")
            continue
        hits.extend(
            f"{relative}: {item}" for item in _missing_classification_data(tree)
        )
    assert hits == []
