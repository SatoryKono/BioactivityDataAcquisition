"""Freeze guard for the deprecated minimal value-object RunManifest."""

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


def _iter_run_manifest_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    root_prefix: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        if py_file in allowed_files:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == SRC_RUN_MANIFEST_MODULE:
                    violations.append(
                        f"{rel_path}:{node.lineno} imports {SRC_RUN_MANIFEST_MODULE}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == SRC_RUN_MANIFEST_MODULE:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {SRC_RUN_MANIFEST_MODULE}"
                        )
    return violations


@pytest.mark.architecture
def test_deprecated_value_object_run_manifest_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Repo source must use runtime contexts or control-plane manifest instead."""
    violations = _iter_run_manifest_import_violations(
        source_ast_cache,
        root_prefix="src",
        allowed_files=frozenset({RUN_MANIFEST_MODULE}),
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
        root_prefix="tests",
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
    """The value_objects public facade must not re-export the deprecated artifact."""
    source = VALUE_OBJECTS_FACADE.read_text(encoding="utf-8")
    assert "run_manifest" not in source
    assert '"RunManifest"' not in source
    assert "'RunManifest'" not in source
