import ast
from pathlib import Path
from bioetl.domain.composite.state import CompositePipelineState

def _find_usage_in_directory(dir_path: Path, member_name: str) -> bool:
    """Find if a specific enum member is used in the given directory."""
    usage_pattern = f"CompositePipelineState.{member_name}"

    for file_path in dir_path.rglob("*.py"):
        if not file_path.is_file():
            continue

        content = file_path.read_text(encoding="utf-8")
        if usage_pattern in content:
            return True

        if f"from bioetl.domain.composite.state import {member_name}" in content:
            return True

        if f"from bioetl.domain.composite import {member_name}" in content:
            return True

    return False

def test_no_dead_composite_pipeline_states():
    """All CompositePipelineState members MUST be used outside of domain/tests.

    This guard catches synthetic dead states that have no application usage.
    """
    src_dir = Path("src/bioetl")

    app_dir = src_dir / "application"
    domain_dir = src_dir / "domain"

    assert app_dir.exists()

    dead_members = []

    for member in CompositePipelineState:
        member_name = member.name

        # Check usage in application
        is_used = _find_usage_in_directory(app_dir, member_name)

        # If not in application, check domain (excluding state.py itself)
        if not is_used:
            for f in domain_dir.rglob("*.py"):
                if f.name == "state.py":
                    continue
                if f"CompositePipelineState.{member_name}" in f.read_text(encoding="utf-8"):
                    is_used = True
                    break

        if not is_used:
            dead_members.append(member_name)

    assert not dead_members, f"Found dead CompositePipelineState members with no application/domain usage: {dead_members}"
