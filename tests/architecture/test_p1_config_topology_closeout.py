"""Closeout ratchets for P1 config-topology ownership seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CONFIG_TOPOLOGY_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/composition/factories/pipeline/registry_manifest.py": (
        25,
        {
            "bioetl.composition.factories.pipeline._registry_manifest_chembl",
            "bioetl.composition.factories.pipeline._registry_manifest_non_chembl",
            "bioetl.composition.factories.pipeline.config_types",
        },
    ),
    "src/bioetl/infrastructure/config/composite_config_api.py": (
        115,
        {
            "bioetl.infrastructure.config._composite_dq_externalization",
            "bioetl.infrastructure.schemas.composite_config",
        },
    ),
    "src/bioetl/infrastructure/config/dq_config_loader.py": (
        255,
        {
            "bioetl.infrastructure.config._dq_config_layers",
            "bioetl.infrastructure.config._dq_config_normalization",
            "bioetl.infrastructure.config._dq_config_validation_merge",
            "bioetl.infrastructure.config.base_config_loader",
            "bioetl.infrastructure.config.dq_config_resolution",
        },
    ),
    "src/bioetl/infrastructure/config/pipeline_config_loader.py": (
        145,
        {
            "bioetl.infrastructure.config.dq_config_loader",
            "bioetl.infrastructure.config.filter_config_loader",
            "bioetl.infrastructure.config.pipeline_config_api",
            "bioetl.infrastructure.config.pipeline_dq_resolution",
        },
    ),
}

FORBIDDEN_IMPORT_PREFIXES: dict[str, tuple[str, ...]] = {
    "src/bioetl/composition/factories/pipeline/registry_manifest.py": (
        "bioetl.infrastructure.config",
    ),
    "src/bioetl/infrastructure/config/composite_config_api.py": ("bioetl.composition",),
    "src/bioetl/infrastructure/config/dq_config_loader.py": ("bioetl.composition",),
    "src/bioetl/infrastructure/config/pipeline_config_loader.py": (
        "bioetl.composition",
    ),
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


@pytest.mark.architecture
def test_retired_composite_config_runtime_compat_file_stays_absent() -> None:
    """Composite config loading must stay owned by _composite_plan_support."""
    assert not _path(
        "src/bioetl/composition/bootstrap/runtime/_composite_config_runtime_compat.py"
    ).exists()


def _tree(relative_path: str) -> ast.Module:
    return ast.parse(_path(relative_path).read_text(encoding="utf-8"))


def _current_package_parts(relative_path: str) -> list[str]:
    src_relative = Path(relative_path).relative_to("src")
    return list(src_relative.with_suffix("").parts[:-1])


def _normalize_import_from_module(
    relative_path: str, node: ast.ImportFrom
) -> str | None:
    if node.module is None:
        return None
    if node.level == 0:
        return node.module

    package_parts = _current_package_parts(relative_path)
    anchor_parts = package_parts[: len(package_parts) - (node.level - 1)]
    return ".".join([*anchor_parts, *node.module.split(".")])


def _imported_modules(relative_path: str) -> set[str]:
    imported_modules: set[str] = set()
    for node in ast.walk(_tree(relative_path)):
        if isinstance(node, ast.ImportFrom):
            normalized_module = _normalize_import_from_module(relative_path, node)
            if normalized_module is not None:
                imported_modules.add(normalized_module)
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
    return imported_modules


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (
            max_lines,
            required_modules,
        ) in CONFIG_TOPOLOGY_RATCHETS.items()
    ],
)
def test_p1_config_topology_surfaces_stay_bounded_and_helper_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """P1 seams should stay thin and routed through their helper owners."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(max {max_lines}). Keep the P1 config-topology seam narrow and move "
        "new logic into its helper owners."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports required helper owners:\n"
        + "\n".join(sorted(missing_modules))
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "forbidden_prefixes"),
    list(FORBIDDEN_IMPORT_PREFIXES.items()),
)
def test_p1_config_topology_surfaces_avoid_forbidden_import_prefixes(
    relative_path: str,
    forbidden_prefixes: tuple[str, ...],
) -> None:
    """P1 ownership seams should not reintroduce forbidden namespace coupling."""
    imported_modules = _imported_modules(relative_path)
    violations = {
        module_name
        for module_name in imported_modules
        if module_name.startswith(forbidden_prefixes)
    }
    assert not violations, (
        f"{relative_path} reintroduced forbidden ownership imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_registry_manifest_stays_assembly_only_without_local_logic_defs() -> None:
    """The registry manifest should remain declarative assembly data, not logic."""
    local_defs = {
        node.name
        for node in _tree(
            "src/bioetl/composition/factories/pipeline/registry_manifest.py"
        ).body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not local_defs, (
        "registry_manifest.py should stay assembly-only and avoid local logic "
        "definitions:\n" + "\n".join(sorted(local_defs))
    )


@pytest.mark.architecture
def test_registry_manifest_imports_only_sanctioned_assembly_modules() -> None:
    """The registry manifest must remain a pure assembly seam over prepared tuples."""
    imported_modules = _imported_modules(
        "src/bioetl/composition/factories/pipeline/registry_manifest.py"
    )
    unexpected_modules = imported_modules - {
        "bioetl.composition.factories.pipeline._registry_manifest_chembl",
        "bioetl.composition.factories.pipeline._registry_manifest_non_chembl",
        "bioetl.composition.factories.pipeline.config_types",
        "__future__",
    }
    assert not unexpected_modules, (
        "registry_manifest.py should import only manifest tuple owners and "
        "PipelineFactoryConfig:\n" + "\n".join(sorted(unexpected_modules))
    )


@pytest.mark.architecture
def test_registry_manifest_avoids_loader_yaml_and_normalization_modules() -> None:
    """The registry manifest must not absorb config loading or normalization work."""
    imported_modules = _imported_modules(
        "src/bioetl/composition/factories/pipeline/registry_manifest.py"
    )
    forbidden_prefixes = (
        "bioetl.infrastructure.config",
        "bioetl.infrastructure.config_load_api",
        "bioetl.infrastructure.config_loader",
        "bioetl.infrastructure.config_loader_filtering",
        "bioetl.infrastructure.config_merge",
        "yaml",
        "ruamel",
    )
    violations = {
        module_name
        for module_name in imported_modules
        if module_name.startswith(forbidden_prefixes)
    }
    assert not violations, (
        "registry_manifest.py must stay assembly-only and avoid YAML/loading/"
        "normalization imports:\n" + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_runtime_inputs_resolver_uses_runtime_config_access_seam() -> None:
    """Runtime input resolution should use the local config-access seam."""
    imported_modules = _imported_modules(
        "src/bioetl/composition/runtime_builders/inputs_resolver.py"
    )
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules, (
        "inputs_resolver.py must use the runtime config_access seam."
    )
    assert (
        "bioetl.infrastructure.config.source_config_loader" not in imported_modules
    ), "inputs_resolver.py must not import source_config_loader directly."


@pytest.mark.architecture
@pytest.mark.parametrize(
    "relative_path",
    [
        "src/bioetl/composition/factories/datasource/http_client.py",
        "src/bioetl/composition/factories/datasource/pubchem.py",
        "src/bioetl/composition/providers/_config_helpers.py",
        "src/bioetl/composition/runtime_builders/config_access.py",
    ],
)
def test_composition_source_config_consumers_use_composition_seam(
    relative_path: str,
) -> None:
    """Composition source-config consumers should import the infrastructure owner."""
    imported_modules = _imported_modules(relative_path)
    assert "bioetl.infrastructure.config.source_config_loader" in imported_modules, (
        f"{relative_path} should import bioetl.infrastructure.config.source_config_loader "
        "as the canonical owner for source-config loading."
    )
    assert "bioetl.composition.source_config_access" not in imported_modules, (
        f"{relative_path} should not depend on the retired "
        "bioetl.composition.source_config_access seam."
    )
