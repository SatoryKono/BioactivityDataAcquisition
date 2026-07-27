"""Tests for release and governance version consistency."""

from __future__ import annotations

pytestmark = pytest.mark.unit


import pytest

from scripts.engineering.repo.check_version_consistency import (
    VersionCheckError,
    extract_docs_governance_version,
    extract_rules_version,
)


def test_release_and_governance_versions_are_separate_concepts() -> None:
    """A docs governance baseline is parsed independently of package release."""
    docs = (
        "# Project\n\n"
        "## Current Version\n\n"
        "**v6.1.5** (governance baseline per [RULES.md](RULES.md))\n"
    )

    assert extract_docs_governance_version(docs) == "6.1.5"
    assert extract_rules_version("Version: 6.1.5\nStatus: active\n") == "6.1.5"


def test_docs_governance_parser_rejects_unclassified_version() -> None:
    """A generic bold version must not be mistaken for governance metadata."""
    with pytest.raises(VersionCheckError, match="governance baseline"):
        extract_docs_governance_version("Current package: **v6.1.0**")
