"""Architecture guardrails for legacy root script compatibility wrappers."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CURRENT_TEST_FILE = Path(__file__).resolve()
_LEGACY_ROOT_WRAPPER_PATHS = frozenset(
    {
        "scripts/docker-setup.ps1",
        "scripts/docker-setup.sh",
        "scripts/startup.ps1",
        "scripts/startup.sh",
        "scripts/shutdown.ps1",
        "scripts/shutdown.sh",
    }
)
_SCANNED_SUFFIXES = {".md", ".py", ".ps1", ".sh"}
_ALLOWED_MENTION_FILES = frozenset(
    {
        CURRENT_TEST_FILE,
        ROOT / "scripts" / "docker-setup.ps1",
        ROOT / "scripts" / "docker-setup.sh",
        ROOT / "scripts" / "startup.ps1",
        ROOT / "scripts" / "startup.sh",
        ROOT / "scripts" / "shutdown.ps1",
        ROOT / "scripts" / "shutdown.sh",
    }
)
_SCAN_ROOTS = (
    ROOT / "docs",
    ROOT / "src",
    ROOT / "tests",
    ROOT / "scripts",
)
_SKIPPED_ROOTS = {
    ROOT / "docs" / "reports",
    ROOT / "docs" / "99-archive",
}


def _iter_repo_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path in seen:
                continue
            if any(skipped in path.parents for skipped in _SKIPPED_ROOTS):
                continue
            if path.suffix not in _SCANNED_SUFFIXES:
                continue
            try:
                is_file = path.is_file()
            except OSError:
                continue
            if not is_file:
                continue
            seen.add(path)
            files.append(path)
    return files


def _iter_legacy_wrapper_mentions() -> list[str]:
    violations: list[str] = []
    for path in _iter_repo_files():
        if path in _ALLOWED_MENTION_FILES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel_path = path.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(lines, start=1):
            for legacy_path in _LEGACY_ROOT_WRAPPER_PATHS:
                if legacy_path in line:
                    violations.append(f"{rel_path}:{lineno} mentions {legacy_path}")
    return violations


@pytest.mark.architecture
def test_legacy_root_script_wrapper_mentions_are_confined_to_sanctioned_surfaces() -> (
    None
):
    """Legacy root script wrappers must not regain new first-party references."""
    violations = _iter_legacy_wrapper_mentions()
    assert not violations, (
        "Legacy root script wrappers leaked beyond sanctioned compatibility surfaces:\n"
        + "\n".join(violations)
    )
