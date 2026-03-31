"""Guardrails for provider registry decomposition."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
REGISTRY_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "provider_registry.py"
)
DEFAULT_REGISTRY_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "_default_registry.py"
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
DEFAULT_REGISTRY_MAX_LINES = 130
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
FORBIDDEN_DEFAULT_REGISTRY_IMPORTS = {
    "bioetl.composition.providers._creation",
    "bioetl.composition.providers._loading",
    "bioetl.composition.providers._store",
    "bioetl.composition.providers.loader",
    "bioetl.composition.providers.registration",
}
CANONICAL_PROVIDER_CONFIG_BUILDERS = {
    "build_data_source_provider_config",
    "build_http_provider_config",
}
ALLOWED_PRIVATE_DEFAULT_REGISTRY_IMPORT_SRC_FILES = {
    REGISTRY_PATH,
    REGISTRATION_PATH,
}
ALLOWED_DEFAULT_PROVIDER_REGISTRY_CALL_SRC_FILES = {
    DEFAULT_REGISTRY_PATH,
    REGISTRY_PATH,
    REGISTRATION_PATH,
}
ALLOWED_DEFAULT_PROVIDER_REGISTRAR_CALL_SRC_FILES: set[Path] = set()


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


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _call_line_numbers(path: Path, function_name: str) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == function_name)
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == function_name
                )
            )
        }
    )


def _iter_named_callsite_violations(
    *,
    root: Path,
    function_name: str,
    allowed_files: set[Path],
) -> list[str]:
    violations: list[str] = []
    for path in _iter_python_files(root):
        if path in allowed_files:
            continue
        for line in _call_line_numbers(path, function_name):
            violations.append(f"{path.relative_to(ROOT)}:{line}")
    return violations


def _iter_module_import_violations(
    *,
    root: Path,
    module_name: str,
    allowed_files: set[Path],
) -> list[str]:
    violations: list[str] = []
    for path in _iter_python_files(root):
        if path in allowed_files:
            continue
        imported_modules = _import_from_modules(path)
        if module_name in imported_modules:
            violations.append(f"{path.relative_to(ROOT)}")
    return violations


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
def test_provider_registry_keeps_default_singleton_in_private_helper() -> None:
    """Default singleton ownership should stay in `_default_registry`."""
    source = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "def get_default_provider_registry(" not in source, (
        "provider_registry.py must not own the lazy default singleton again. "
        "Keep default-registry state in _default_registry.py."
    )
    assert "def get_default_provider_registrar(" not in source, (
        "provider_registry.py must not reintroduce a local default-registrar "
        "helper. Keep the compat seam private in _default_registry.py."
    )
    assert "_default_provider_registry: ProviderRegistry | None =" not in source, (
        "provider_registry.py must not grow a module-level default singleton "
        "slot again."
    )


@pytest.mark.architecture
def test_default_registry_helper_stays_thin_and_private() -> None:
    """`_default_registry.py` should remain a tiny compat owner, not a new facade hub."""
    source = DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= DEFAULT_REGISTRY_MAX_LINES, (
        f"_default_registry.py grew to {line_count} lines "
        f"(max {DEFAULT_REGISTRY_MAX_LINES}). Keep default-registry ownership "
        "narrow and compat-focused."
    )

    imported_modules = _import_from_modules(DEFAULT_REGISTRY_PATH)
    unexpected_imports = FORBIDDEN_DEFAULT_REGISTRY_IMPORTS & imported_modules
    assert not unexpected_imports, (
        "_default_registry.py must not absorb registry creation/loading logic:\n"
        + "\n".join(sorted(unexpected_imports))
    )

    assert "def get_default_provider_registry(" in source, (
        "_default_registry.py must keep the lazy singleton seam explicit."
    )
    assert "def get_default_provider_registrar(" in source, (
        "_default_registry.py must keep the named compat registrar seam explicit."
    )
    assert "_default_provider_registry: ProviderRegistry | None = None" in source, (
        "_default_registry.py must remain the owner of the lazy singleton slot."
    )


@pytest.mark.architecture
def test_private_default_registry_module_imports_stay_confined_to_sanctioned_seams() -> (
    None
):
    """`_default_registry` must remain a private compat helper, not a general import target."""
    violations = _iter_module_import_violations(
        root=SRC_ROOT,
        module_name="bioetl.composition.providers._default_registry",
        allowed_files=ALLOWED_PRIVATE_DEFAULT_REGISTRY_IMPORT_SRC_FILES,
    )
    assert not violations, (
        "Raw imports of composition.providers._default_registry leaked into new "
        "src call sites:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_default_provider_registry_raw_calls_stay_confined_to_known_src_baseline() -> (
    None
):
    """Lazy default-registry access must stay limited to the sanctioned compat seams."""
    violations = _iter_named_callsite_violations(
        root=SRC_ROOT,
        function_name="get_default_provider_registry",
        allowed_files=ALLOWED_DEFAULT_PROVIDER_REGISTRY_CALL_SRC_FILES,
    )
    assert not violations, (
        "get_default_provider_registry() leaked into new src call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_default_provider_registrar_raw_calls_stay_confined_to_known_src_baseline() -> (
    None
):
    """Named registrar seam should remain local to the sanctioned compat entrypoints."""
    violations = _iter_named_callsite_violations(
        root=SRC_ROOT,
        function_name="get_default_provider_registrar",
        allowed_files=ALLOWED_DEFAULT_PROVIDER_REGISTRAR_CALL_SRC_FILES,
    )
    assert not violations, (
        "get_default_provider_registrar() leaked into new src call sites:\n"
        + "\n".join(violations)
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
