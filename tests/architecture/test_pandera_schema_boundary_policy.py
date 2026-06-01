"""Architecture guardrails for Pandera/Pandas schema boundary policy."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = ROOT / "src" / "bioetl" / "domain"
ADR_PATH = (
    ROOT
    / "docs"
    / "02-architecture"
    / "decisions"
    / "ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md"
)

_ALLOWED_DOMAIN_SCHEMA_PREFIXES = (
    "src/bioetl/domain/schemas/",
    "src/bioetl/domain/contracts/",
)
_DATAFRAME_SCHEMA_MODULES = {"pandas", "pandera"}


def _imports_dataframe_schema_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name.split(".", 1)[0] in _DATAFRAME_SCHEMA_MODULES
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".", 1)[0] in _DATAFRAME_SCHEMA_MODULES:
                return True
    return False


def test_domain_dataframe_schema_imports_are_confined_to_contract_packages() -> None:
    """Domain may model dataframe contracts but must not leak them into behavior."""
    offenders: list[str] = []
    for path in DOMAIN_ROOT.rglob("*.py"):
        if not _imports_dataframe_schema_module(path):
            continue
        rel_path = path.relative_to(ROOT).as_posix()
        if not rel_path.startswith(_ALLOWED_DOMAIN_SCHEMA_PREFIXES):
            offenders.append(rel_path)

    assert not offenders, (
        "Pandera/Pandas imports in domain are sanctioned only for schema-contract "
        "packages, not behavior/services/value objects:\n" + "\n".join(offenders)
    )


def test_runtime_pandera_compatibility_patch_is_not_package_import_side_effect() -> (
    None
):
    """Pandera compatibility patching must remain an explicit runtime bootstrap call."""
    top_level_init = (ROOT / "src" / "bioetl" / "__init__.py").read_text(
        encoding="utf-8"
    )
    runtime_init = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    runtime_patch = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "compatibility.py"
    ).read_text(encoding="utf-8")

    assert "apply_pandera_typing_compat_if_needed()" not in top_level_init
    assert "apply_pandera_typing_compat_if_needed()" not in runtime_init
    assert "apply_runtime_compatibility_patches" in runtime_init
    assert "apply_pandera_typing_compat_if_needed" in runtime_patch


def test_adr_048_records_schema_boundary_and_runtime_patch_decisions() -> None:
    """The Pandera boundary must stay backed by an accepted ADR."""
    text = ADR_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    for expected in (
        "Status: Accepted",
        "schema-contract representation",
        "not adapter implementations",
        "No import-time compatibility patching",
        "apply_runtime_compatibility_patches",
    ):
        assert expected in normalized_text
