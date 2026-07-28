"""Unit tests for documentation governance sync checks."""

from __future__ import annotations

import pytest

from scripts.documentation_governance_check import DocumentationGovernanceChecker


pytestmark = pytest.mark.unit


def test_adr_registry_sync_check_passes_on_current_repository() -> None:
    checker = DocumentationGovernanceChecker()

    passed, warnings, results = checker.check_adr_registry_sync()

    assert passed, results
    assert warnings == []
    assert results == ["ADR registry mirrors are synchronized through ADR-052"]
