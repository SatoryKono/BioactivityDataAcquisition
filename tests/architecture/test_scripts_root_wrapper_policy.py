"""Architecture policy: scripts root stays directories-only in the final layout."""

from __future__ import annotations

from pathlib import Path


_EXPECTED_TOP_LEVEL_DIRS = (
    "ai",
    "diagrams",
    "docs",
    "engineering",
    "memory",
    "ops",
    "schema",
)


def test_scripts_root_matches_final_canonical_layout() -> None:
    """scripts/ root must expose only the final seven canonical top-level directories."""
    root = Path("scripts")
    assert root.exists(), "scripts directory must exist"

    entries = sorted(root.iterdir(), key=lambda item: item.name)
    files = [entry.name for entry in entries if entry.is_file()]
    assert not files, (
        "scripts/ root must not contain files in the final layout:\n"
        + "\n".join(f"  - {name}" for name in files)
    )

    directory_names = [entry.name for entry in entries if entry.is_dir()]
    assert directory_names == list(_EXPECTED_TOP_LEVEL_DIRS), (
        "scripts/ root must contain exactly the canonical top-level directories:\n"
        f"expected: {_EXPECTED_TOP_LEVEL_DIRS}\n"
        f"actual: {tuple(directory_names)}"
    )
