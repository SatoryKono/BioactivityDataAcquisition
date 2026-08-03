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
"""Unit tests for schema classifier governance gate helpers."""

from __future__ import annotations

import pytest

from scripts.engineering.ci.validate_schema_classifier_gate import (
    _major_transition_issues,
)


pytestmark = pytest.mark.unit


def test_major_transition_requires_major_bump_and_migration_key() -> None:
    """Major classification must fail without major bump and migration guide."""
    issues = _major_transition_issues(
        contract_ref="chembl.activity",
        old_version="1.0.0",
        new_version="1.0.0",
        migration_guides={},
    )
    messages = [issue.message for issue in issues]
    assert any("major version bump" in message for message in messages)
    assert any("migration_guides entry" in message for message in messages)


def test_major_transition_passes_with_major_bump_and_guide() -> None:
    """Major classification should pass when bump + migration guide are present."""
    issues = _major_transition_issues(
        contract_ref="chembl.activity",
        old_version="1.0.0",
        new_version="2.0.0",
        migration_guides={"1.0.0->2.0.0": "docs/migrations/chembl-activity-2.0.md"},
    )
    assert issues == []
