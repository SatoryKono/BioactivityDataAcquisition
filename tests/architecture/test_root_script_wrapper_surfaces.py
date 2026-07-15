"""Architecture guardrails for legacy root script wrapper surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.git_index_scan import git_grep_fixed

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
        ROOT / "tests" / "architecture" / "test_docker_runtime_contracts.py",
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
    "src/memory/",
    "scripts/archive/",
)


def _iter_legacy_wrapper_mentions() -> list[str]:
    matches = git_grep_fixed(
        root=ROOT,
        patterns=tuple(sorted(_LEGACY_ROOT_WRAPPER_PATHS)),
        paths=_GIT_SCAN_PATHS,
        excluded_prefixes=_SKIPPED_PATH_PREFIXES,
        suffixes=_SCANNED_SUFFIXES,
        timeout=10.0,
    )

    violations: list[str] = []
    for match in matches:
        if not match.path.endswith(_SCANNED_SUFFIXES):
            continue
        if match.path in _ALLOWED_MENTION_PATHS:
            continue
        if any(match.path.startswith(prefix) for prefix in _SKIPPED_PATH_PREFIXES):
            continue
        for legacy_path in _LEGACY_ROOT_WRAPPER_PATHS:
            if legacy_path in match.text:
                violations.append(
                    f"{match.path}:{match.line_number} mentions {legacy_path}"
                )
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
