from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

def test_no_legacy_validation_test_debt_markers() -> None:
    """Validation test modules should not keep stale debt marker comments."""
    targets = {
        Path("tests/integration/validation/test_external_verification.py"): (
            "TODO: Add remaining external verification tests",
            "Total expected: ~40 tests",
        ),
        Path("tests/unit/application/services/dq/test_structural_validation.py"): (
            "TODO: Add remaining ~40 structural validation tests",
        ),
        Path("tests/unit/application/services/dq/test_logical_validation.py"): (
            "TODO: Add remaining ~40 logical validation tests",
        ),
    }

    violations: list[str] = []
    for path, markers in targets.items():
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker in text:
                violations.append(f"{path.as_posix()}: {marker}")

    assert not violations, "Legacy validation test-debt markers found:\n" + "\n".join(
        f"  - {item}" for item in violations
    )
