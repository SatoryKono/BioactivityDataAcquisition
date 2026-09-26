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
"""Contract checks for generic semantic field ownership."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.check_generic_field_ownership import (
    DEFAULT_OWNERSHIP_PATH,
    validate_generic_field_ownership,
)


pytestmark = pytest.mark.integration


def test_generic_field_ownership_gate_passes_current_repo() -> None:
    findings = validate_generic_field_ownership(repo_root=Path("."))

    assert not findings, "\n".join(finding.message for finding in findings)


def test_generic_field_ownership_registry_names_denied_terms() -> None:
    payload = yaml.safe_load(DEFAULT_OWNERSHIP_PATH.read_text(encoding="utf-8"))

    assert {
        "description",
        "relation",
        "score",
        "source",
        "status",
        "type",
        "value",
    } <= set(payload["denied_terms"])


def test_generic_field_ownership_entries_have_required_metadata() -> None:
    payload = yaml.safe_load(DEFAULT_OWNERSHIP_PATH.read_text(encoding="utf-8"))

    for entry in payload["entries"]:
        assert entry["owner"]
        assert entry["semantic_role"]
        assert entry["rationale"]
        assert entry["surface"]
        assert entry["path"]
        assert entry["context"]
        assert entry["fields"]
