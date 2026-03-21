"""Guardrails for provider registry decomposition."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "provider_registry.py"
)
REGISTRATION_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "registration.py"
)
REGISTRATION_BIO_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "registration_bio.py"
)
CONFIG_HELPERS_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "_config_helpers.py"
)
REGISTRATION_BIBLIO_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "registration_biblio.py"
)
FACTORY_LOADER_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "factory_loader.py"
)
REGISTRY_MAX_LINES = 260  # bumped: RF-001 added __init__, RLock, lazy singleton
REQUIRED_HELPER_IMPORTS = {
    "bioetl.composition.providers._creation",
    "bioetl.composition.providers._models",
    "bioetl.composition.providers._store",
}
FORBIDDEN_REGISTRY_RUNTIME_IMPORTS = {
    "bioetl.composition.providers.loader",
}
FORBIDDEN_REGISTRATION_IMPORTS = {
    "bioetl.composition.providers.registration",
    "bioetl.composition.providers.registration_bio",
    "bioetl.composition.providers.registration_biblio",
}
FORBIDDEN_REVERSE_REGISTRATION_IMPORTS = {
    "bioetl.composition.providers.provider_registry",
}
FORBIDDEN_FACTORY_LOADER_IMPORTS = {
    "bioetl.composition.providers.factory_loader",
}
CANONICAL_PROVIDER_CONFIG_BUILDERS = {
    "build_data_source_provider_config",
    "build_http_provider_config",
}


def _import_from_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            called_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            called_names.add(func.attr)
    return called_names


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
    unexpected_runtime_imports = FORBIDDEN_REGISTRY_RUNTIME_IMPORTS & imported_modules
    assert not unexpected_runtime_imports, (
        "provider_registry.py must not reach back into public loader facades:\n"
        + "\n".join(sorted(unexpected_runtime_imports))
    )
    unexpected_registration_imports = FORBIDDEN_REGISTRATION_IMPORTS & imported_modules
    assert not unexpected_registration_imports, (
        "provider_registry.py must not absorb provider registration logic again:\n"
        + "\n".join(sorted(unexpected_registration_imports))
    )


@pytest.mark.architecture
def test_provider_registry_keeps_loader_indirection_seam() -> None:
    """Provider registry may late-bind `_loading`, but must keep the seam explicit."""
    source = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "_ensure_registry_loaded" in source, (
        "provider_registry.py must keep an explicit loader indirection helper "
        "instead of inlining provider bootstrap logic."
    )
    assert "bioetl.composition.providers._loading" in source, (
        "provider_registry.py must still target the private `_loading` helper "
        "module, even when it is late-bound to avoid import-cycle pressure."
    )


@pytest.mark.architecture
def test_registration_module_stays_decoupled_from_provider_registry() -> None:
    """Registration assembly should target injected registries, not the facade singleton."""
    imported_modules = _import_from_modules(REGISTRATION_PATH)
    unexpected_registry_imports = (
        FORBIDDEN_REVERSE_REGISTRATION_IMPORTS & imported_modules
    )
    assert not unexpected_registry_imports, (
        "registration.py must assemble configs against injected registries, "
        "not import ProviderRegistry directly:\n"
        + "\n".join(sorted(unexpected_registry_imports))
    )


@pytest.mark.architecture
@pytest.mark.parametrize("path", [REGISTRATION_BIO_PATH, CONFIG_HELPERS_PATH])
def test_registration_helpers_use_injected_assembly_callbacks(path: Path) -> None:
    """Provider registration helpers should not rely on lazy factory-loader lookups."""
    imported_modules = _import_from_modules(path)
    unexpected_factory_loader_imports = (
        FORBIDDEN_FACTORY_LOADER_IMPORTS & imported_modules
    )
    assert not unexpected_factory_loader_imports, (
        f"{path.name} must not import factory_loader after RF-FS-001:\n"
        + "\n".join(sorted(unexpected_factory_loader_imports))
    )


@pytest.mark.architecture
@pytest.mark.parametrize("path", [REGISTRATION_BIO_PATH, REGISTRATION_BIBLIO_PATH])
def test_registration_family_uses_canonical_provider_config_builders(
    path: Path,
) -> None:
    """Bio/biblio registration families should not grow manual ProviderConfig skeletons."""
    called_names = _called_names(path)
    assert "ProviderConfig" not in called_names, (
        f"{path.name} must not manually construct ProviderConfig entries again. "
        "Use canonical builder helpers from _registration_contracts instead."
    )

    imported_modules = _import_from_modules(path)
    assert "bioetl.composition.providers._registration_contracts" in imported_modules, (
        f"{path.name} must import canonical provider-config builders from "
        "_registration_contracts."
    )

    missing_builders = CANONICAL_PROVIDER_CONFIG_BUILDERS & called_names
    assert missing_builders, (
        f"{path.name} must call at least one canonical provider-config builder "
        "from _registration_contracts."
    )


@pytest.mark.architecture
def test_factory_loader_module_stays_removed() -> None:
    """The old factory_loader compat seam should stay removed."""
    assert not FACTORY_LOADER_PATH.exists(), (
        "composition/providers/factory_loader.py must stay removed after "
        "RF-FS-001 cleanup."
    )
