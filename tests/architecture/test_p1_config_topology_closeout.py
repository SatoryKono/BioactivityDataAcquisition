"""Closeout ratchets for P1 config-topology ownership seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CONFIG_TOPOLOGY_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/composition/factories/pipeline/registry_manifest.py": (
        40,
        {
            "bioetl.composition.factories.pipeline._registry_manifest_chembl",
            "bioetl.composition.factories.pipeline._registry_manifest_non_chembl",
            "bioetl.composition.factories.pipeline.config_types",
        },
    ),
    "src/bioetl/infrastructure/config/dq_config_loader.py": (
        285,
        {
            "bioetl.infrastructure.config._dq_config_layers",
            "bioetl.infrastructure.config._dq_config_normalization",
            "bioetl.infrastructure.config._dq_config_validation_merge",
            "bioetl.infrastructure.config.base_config_loader",
            "bioetl.infrastructure.config.dq_config_resolution",
        },
    ),
    "src/bioetl/infrastructure/config/pipeline_config_loader.py": (
        210,
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
    "src/bioetl/infrastructure/config/dq_config_loader.py": ("bioetl.composition",),
    "src/bioetl/infrastructure/config/pipeline_config_loader.py": (
        "bioetl.composition",
    ),
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


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
