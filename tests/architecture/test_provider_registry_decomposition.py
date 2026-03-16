"""Guardrails for provider registry decomposition."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "provider_registry.py"
)
REGISTRY_MAX_LINES = 260  # bumped: RF-001 added __init__, RLock, lazy singleton
REQUIRED_HELPER_IMPORTS = {
    "bioetl.composition.providers._creation",
    "bioetl.composition.providers._models",
    "bioetl.composition.providers._store",
}
FORBIDDEN_REGISTRATION_IMPORTS = {
    "bioetl.composition.providers.registration",
    "bioetl.composition.providers.registration_bio",
    "bioetl.composition.providers.registration_biblio",
}


def _import_from_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
def test_provider_registry_facade_does_not_grow() -> None:
    """Provider registry facade should stay thin after RF-016 decomposition."""
    line_count = len(REGISTRY_PATH.read_text(encoding="utf-8").splitlines())
    assert line_count <= REGISTRY_MAX_LINES, (
        f"provider_registry.py grew to {line_count} lines "
        f"(max {REGISTRY_MAX_LINES}). "
        "Move new provider wiring into helper modules or registrar modules."
    )


@pytest.mark.architecture
def test_provider_registry_uses_split_helper_modules() -> None:
    """Provider registry should remain a facade over helper modules."""
    imported_modules = _import_from_modules(REGISTRY_PATH)
    missing_helpers = REQUIRED_HELPER_IMPORTS - imported_modules
    assert not missing_helpers, (
        "provider_registry.py no longer imports required split helpers:\n"
        + "\n".join(sorted(missing_helpers))
    )
    unexpected_registration_imports = FORBIDDEN_REGISTRATION_IMPORTS & imported_modules
    assert not unexpected_registration_imports, (
        "provider_registry.py must not absorb provider registration logic again:\n"
        + "\n".join(sorted(unexpected_registration_imports))
    )
