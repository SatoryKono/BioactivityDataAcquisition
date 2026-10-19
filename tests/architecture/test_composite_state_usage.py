from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.domain.composite.state import CompositePipelineState


def _used_attributes(file_path: Path, class_name: str) -> set[str]:
    """Return accessed attributes of ``class_name`` found in a Python file."""
    if not file_path.exists():
        return set()

    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == class_name
    }


@pytest.mark.architecture
def test_no_dead_composite_pipeline_states():
    """Each state must have a real reference outside the state enum and tests."""
    src_dir = Path("src/bioetl")
    search_dirs = (
        src_dir / "application",
        src_dir / "infrastructure",
        src_dir / "interfaces",
        src_dir / "domain",
    )

    used_members: set[str] = set()
    for directory in search_dirs:
        if not directory.exists():
            continue
        for file_path in directory.rglob("*.py"):
            if directory.name == "domain" and file_path.name == "state.py":
                continue
            used_members.update(_used_attributes(file_path, "CompositePipelineState"))

    dead_members = [
        member.name
        for member in CompositePipelineState
        if member.name not in used_members
    ]
    assert not dead_members, (
        "Found CompositePipelineState members without application/domain usage: "
        f"{dead_members}"
    )
