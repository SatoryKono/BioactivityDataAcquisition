# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture policy for transitional `scripts/` root wrappers."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture

_CATALOG = Path("scripts/engineering/repo/catalog.yaml")
_REQUIRED_TOP_LEVEL_DIRS = (
    "ai",
    "diagrams",
    "docs",
    "engineering",
    "memory",
    "ops",
    "schema",
)
_COMPATIBILITY_MARKER = "Compatibility wrapper"


def _load_catalog() -> dict[str, object]:
    with _CATALOG.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    assert isinstance(payload, dict), "scripts catalog must be a mapping"
    return payload


def _root_allowlist() -> set[str]:
    policies = _load_catalog().get("policies", {})
    assert isinstance(policies, dict), "catalog policies must be a mapping"
    allowlist = policies.get("root_allowlist", [])
    assert isinstance(allowlist, list), "catalog root_allowlist must be a list"
    return {str(name) for name in allowlist}


def _is_wrapper_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return _COMPATIBILITY_MARKER in text


def test_scripts_root_matches_wrapper_policy() -> None:
    """scripts/ root may only contain canonical dirs plus allowed compatibility wrappers."""
    root = Path("scripts")
    assert root.exists(), "scripts directory must exist"

    allowlist = _root_allowlist()
    entries = sorted(root.iterdir(), key=lambda item: item.name)

    unexpected_files = []
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name == "__init__.py":
            continue
        if entry.name in allowlist:
            continue
        if _is_wrapper_file(entry):
            continue
        unexpected_files.append(entry.name)

    assert not unexpected_files, (
        "scripts/ root contains non-wrapper files outside the allowlist:\n"
        + "\n".join(f"  - {name}" for name in unexpected_files)
    )

    directory_names = {
        entry.name
        for entry in entries
        if entry.is_dir() and entry.name != "__pycache__"
    }
    missing_dirs = [
        name for name in _REQUIRED_TOP_LEVEL_DIRS if name not in directory_names
    ]
    assert not missing_dirs, (
        "scripts/ root is missing canonical top-level directories:\n"
        + "\n".join(f"  - {name}" for name in missing_dirs)
    )
