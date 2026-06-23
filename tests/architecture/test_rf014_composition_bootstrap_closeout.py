"""Closeout ratchets for RF-014 composition/bootstrap seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

COMPOSITION_BOOTSTRAP_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/composition/factories/pipeline/assembler.py": (
        280,
        {
            "bioetl.composition.factories.datasource.data_source_factory",
            "bioetl.composition.factories.dq.context_resolver",
            "bioetl.composition.factories.pipeline.factory_method_helpers",
            "bioetl.composition.factories.pipeline.runner_assembly",
        },
    ),
    "src/bioetl/composition/bootstrap/runtime/pipeline.py": (
        82,
        {
            "bioetl.composition.bootstrap.runtime.assembly",
            "bioetl.composition.runtime_builders.config_access",
            "bioetl.composition.runtime_builders.runner_builder",
        },
    ),
    "src/bioetl/composition/bootstrap/cli/config.py": (
        65,
        {
            "bioetl.composition.bootstrap.cli.noop",
            "bioetl.composition.runtime_builders.config_access",
            "bioetl.infrastructure.config.converters",
        },
    ),
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _imported_modules(relative_path: str) -> set[str]:
    tree = ast.parse(_path(relative_path).read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (max_lines, required_modules) in (
            COMPOSITION_BOOTSTRAP_RATCHETS.items()
        )
    ],
)
def test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """RF-014 seams should stay thin and routed through helper owners."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(max {max_lines}). Keep the RF-014 composition/bootstrap seam narrow "
        "and move new logic into helper owners."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports required helper owners:\n"
        + "\n".join(sorted(missing_modules))
    )
