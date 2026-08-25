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
"""Architecture tests for validator enforcement in composition factories.

REQ-ARCH-VAL-001: Composition factories MUST NOT use NoOp validators for
Gold/Silver validation in production pipelines.
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture


class TestFactoryValidatorEnforcement:
    """Validate composition factories don't reference NoOp validators."""

    def test_factories_do_not_reference_noop_validators(self, src_dir: Path) -> None:
        """Factories should not reference NoOp Gold/Silver validators."""
        factories_path = src_dir / "bioetl" / "composition" / "factories"
        if not factories_path.exists():
            pytest.skip("Composition factories package not found")

        forbidden_tokens = ("NoOpSilverValidator", "NoOpGoldValidator", "NoOpValidator")
        violations: list[str] = []

        for py_file in factories_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                if token in content:
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(f"{relative_path}: {token}")

        assert not violations, (
            "Composition factories must not reference NoOp validators.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_silver_runtime_helpers_do_not_default_to_noop(self, src_dir: Path) -> None:
        path = src_dir / "bioetl" / "infrastructure" / "storage" / "silver" / "runtime_helpers.py"
        content = path.read_text(encoding="utf-8")
        assert "or NoOpValidator()" not in content
        assert "silver_validator or NoOpValidator" not in content

