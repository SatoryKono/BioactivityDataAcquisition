"""Architecture guardrails against hardcoded mounted-worktree skip debt."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
FORBIDDEN_MARKERS = (
    "Network drive " "timeout",
    "E:\\" "g-drive",
)


def test_tests_do_not_reintroduce_hardcoded_network_drive_skips() -> None:
    offenders: list[str] = []
    this_file = Path(__file__).resolve()

    for test_file in TESTS_DIR.rglob("test_*.py"):
        if test_file.resolve() == this_file:
            continue
        content = test_file.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker in content:
                offenders.append(f"{test_file.relative_to(ROOT)}: {marker}")

    assert not offenders, (
        "Retire hardcoded mounted-worktree skip debt and use local-temp fixtures "
        "or capability bootstrap instead. Offenders:\n"
        + "\n".join(f"  - {offender}" for offender in offenders)
    )
