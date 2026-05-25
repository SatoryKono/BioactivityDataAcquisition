"""Architecture guardrails for legacy root script compatibility wrappers."""

from __future__ import annotations

import os
import subprocess
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
_SCANNED_SUFFIXES = (".md", ".py", ".ps1", ".sh")
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
_ALLOWED_MENTION_PATHS = frozenset(
    path.relative_to(ROOT).as_posix() for path in _ALLOWED_MENTION_FILES
)
_GIT_SCAN_PATHS = ("docs", "src", "tests", "scripts")
_SKIPPED_PATH_PREFIXES = (
    "docs/reports/",
    "docs/99-archive/",
    "docs/site/",
    "docs/exports/",
    "docs/02-architecture/generated/",
    "docs/02-architecture/diagrams/bundles/",
    "docs/02-architecture/diagrams/manifests/",
    "docs/02-architecture/diagrams/png/",
    "docs/02-architecture/diagrams/tooling/",
    "docs/02-architecture/diagrams/architecture/png/",
    "docs/02-architecture/diagrams/architecture/svg/",
    "docs/02-architecture/diagrams/class-diagrams/png/",
    "docs/02-architecture/diagrams/class-diagrams/svg/",
    "docs/02-architecture/diagrams/foundation/png/",
    "docs/02-architecture/diagrams/foundation/svg/",
    "docs/02-architecture/diagrams/views/png/",
    "docs/02-architecture/diagrams/views/svg/",
    "docs/02-architecture/diagrams/descriptions/legacy/",
    "src/memory/episodic/",
    "scripts/archive/",
)


def _iter_legacy_wrapper_mentions() -> list[str]:
    command = ["git", "grep", "-n", "-F"]
    for legacy_path in sorted(_LEGACY_ROOT_WRAPPER_PATHS):
        command.extend(("-e", legacy_path))
    command.append("--")
    command.extend(_GIT_SCAN_PATHS)
    command.extend(
        f":(exclude){path_prefix}**" for path_prefix in _SKIPPED_PATH_PREFIXES
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise AssertionError(f"git grep failed: {result.stderr.strip()}")

    violations: list[str] = []
    for match in result.stdout.splitlines():
        rel_path, lineno, line = match.split(":", 2)
        if not rel_path.endswith(_SCANNED_SUFFIXES):
            continue
        if rel_path in _ALLOWED_MENTION_PATHS:
            continue
        if any(rel_path.startswith(prefix) for prefix in _SKIPPED_PATH_PREFIXES):
            continue
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
