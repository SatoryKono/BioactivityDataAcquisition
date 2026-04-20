"""Freeze guard preventing reintroduction of the removed value-object RunManifest."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_RUN_MANIFEST_MODULE = "bioetl.domain.value_objects.run_manifest"
VALUE_OBJECTS_FACADE = (
    ROOT / "src" / "bioetl" / "domain" / "value_objects" / "__init__.py"
)
RUN_MANIFEST_MODULE = (
    ROOT / "src" / "bioetl" / "domain" / "value_objects" / "run_manifest.py"
)


def _imports_deprecated_run_manifest(node: ast.AST) -> bool:
    if isinstance(node, ast.ImportFrom):
        return node.module == SRC_RUN_MANIFEST_MODULE
    if isinstance(node, ast.Import):
        return any(alias.name == SRC_RUN_MANIFEST_MODULE for alias in node.names)
    return False


def _deprecated_run_manifest_import_violations_for_tree(
    *,
    tree: ast.Module,
    rel_path: str,
) -> list[str]:
    return [
        f"{rel_path}:{node.lineno} imports {SRC_RUN_MANIFEST_MODULE}"
        for node in ast.walk(tree)
        if _imports_deprecated_run_manifest(node)
    ]


def _iter_run_manifest_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        if py_file in allowed_files:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        violations.extend(
            _deprecated_run_manifest_import_violations_for_tree(
                tree=tree,
                rel_path=rel_path,
            )
        )
    return violations


@pytest.mark.architecture
def test_deprecated_value_object_run_manifest_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Repo source must use runtime contexts or control-plane manifest instead."""
    violations = _iter_run_manifest_import_violations(
        source_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Deprecated bioetl.domain.value_objects.run_manifest imports are still used "
        "from src/:\n"
        + "\n".join(violations)
        + "\n\nUse bioetl.domain.context for runtime execution, "
        "bioetl.domain.control_plane.run_manifest for provenance, or "
        "bioetl.domain.value_objects.run_context for metadata flows."
    )


@pytest.mark.architecture
def test_deprecated_value_object_run_manifest_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests should exercise canonical runtime/control-plane contracts instead."""
    violations = _iter_run_manifest_import_violations(
        test_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Deprecated bioetl.domain.value_objects.run_manifest imports are still used "
        "from tests/:\n"
        + "\n".join(violations)
        + "\n\nExercise PipelineRunContext/PipelineContext or "
        "domain.control_plane.RunManifest directly instead."
    )


@pytest.mark.architecture
def test_value_objects_facade_does_not_export_deprecated_run_manifest() -> None:
    """The value_objects public facade must not re-export the removed artifact."""
    source = VALUE_OBJECTS_FACADE.read_text(encoding="utf-8")
    assert "run_manifest" not in source
    assert '"RunManifest"' not in source
    assert "'RunManifest'" not in source


@pytest.mark.architecture
def test_removed_value_object_run_manifest_module_is_not_reintroduced() -> None:
    """The removed module must stay absent from the active source tree."""
    assert not RUN_MANIFEST_MODULE.exists(), (
        "src/bioetl/domain/value_objects/run_manifest.py must remain removed. "
        "Reintroducing it would reopen the deprecated split-manifest surface."
    )
