import ast
import pytest
from pathlib import Path
from bioetl.domain.composite.state import CompositePipelineState


def get_used_attributes(file_path: Path, class_name: str) -> set[str]:
    """Parse Python file and extract accessed attributes of a given class."""
    if not file_path.exists():
        return set()

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return set()

    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == class_name:
                used.add(node.attr)
    return used


@pytest.mark.architecture
def test_no_dead_composite_pipeline_states():
    """All CompositePipelineState members MUST be used outside of domain/tests.

    This guard catches synthetic dead states that have no application usage
    using actual AST parsing.
    """
    src_dir = Path("src/bioetl")

    # We only care about application usage (and infra/interfaces)
    search_dirs = [
        src_dir / "application",
        src_dir / "infrastructure",
        src_dir / "interfaces",
    ]

    used_members = set()

    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            used_members.update(get_used_attributes(f, "CompositePipelineState"))

    # Also check domain, excluding tests and state.py
    domain_dir = src_dir / "domain"
    for f in domain_dir.rglob("*.py"):
        if f.name == "state.py" or "tests" in str(f):
            continue
        used_members.update(get_used_attributes(f, "CompositePipelineState"))

    dead_members = []
    for member in CompositePipelineState:
        if member.name not in used_members:
            dead_members.append(member.name)

    assert not dead_members, (
        f"Found dead CompositePipelineState members with no application/domain usage: {dead_members}"
    )
