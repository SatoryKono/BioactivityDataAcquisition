"""Ratchets for config/checkpoint compatibility test assertion quality."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

TARGETS = (
    ROOT
    / "tests/unit/application/services/test_checkpoint_compatibility_service_v2.py",
)

BANNED_PATTERNS = {
    r"assert\s+len\(result\.recovery_suggestions\)\s*>\s*0": (
        "recovery suggestions must be asserted as explicit lists"
    ),
    r"assert\s+.*result\.message\.lower\(\).*?\bor\b": (
        "compatibility messages must be asserted exactly"
    ),
    r"assert\s+.*suggestions_text.*?\bor\b": (
        "suggestion assertions must check exact ordered outputs"
    ),
}


@pytest.mark.architecture
def test_checkpoint_compatibility_tests_do_not_use_weak_assertion_forms() -> None:
    """Compatibility tests should assert stable invariants, not broad text matches."""
    violations: list[str] = []
    for path in TARGETS:
        content = path.read_text(encoding="utf-8")
        for pattern, reason in BANNED_PATTERNS.items():
            for match in re.finditer(pattern, content):
                line = content.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(ROOT)}:{line}: {reason}")

    assert not violations, (
        "Weak config/checkpoint compatibility assertions found:\n"
        + "\n".join(violations)
    )
