"""Architecture policy: scripts root keeps wrappers, canonical logic lives in subfolders."""

from __future__ import annotations

from pathlib import Path


_ALLOWED_CANONICAL_ROOT_SCRIPTS = {"run.py"}


def test_scripts_root_contains_only_wrappers_or_allowed_entrypoints() -> None:
    """Root scripts must be compatibility wrappers except explicit allowlist."""
    root = Path("scripts")
    assert root.exists(), "scripts directory must exist"

    violations: list[str] = []
    for path in sorted(root.glob("*")):
        if not path.is_file():
            continue
        if path.name == "__init__.py":
            continue
        if path.suffix not in {".py", ".sh", ".ps1", ".cmd", ".bat"}:
            continue

        if path.name in _ALLOWED_CANONICAL_ROOT_SCRIPTS:
            continue

        text = path.read_text(encoding="utf-8")
        if "Compatibility wrapper" not in text:
            violations.append(path.as_posix())

    assert not violations, (
        "Non-wrapper scripts detected in scripts root. "
        "Move canonical logic into scripts/<group>/ and keep root as wrappers:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )
