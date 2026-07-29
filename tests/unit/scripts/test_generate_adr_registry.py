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
"""Regression tests for ADR registry generation."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.generate_adr_registry import ADRRegistryGenerator


pytestmark = pytest.mark.unit

ADR_008_PATH = Path(
    "docs/02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md"
)


def test_extract_adr_metadata_reads_inline_status_date_and_owner() -> None:
    """Generated registry must honor explicit ADR metadata from source docs."""
    generator = ADRRegistryGenerator()

    metadata = generator.extract_adr_metadata(ADR_008_PATH)

    assert metadata is not None
    assert metadata.status == "superseded"
    assert metadata.source_status is not None
    assert metadata.decision_date == "2025-12-22"
    assert metadata.owner == "BioETL Team"


def test_determine_adr_status_maps_accepted_to_accepted_bucket() -> None:
    """Accepted ADRs keep the normalized accepted registry bucket."""
    generator = ADRRegistryGenerator()

    status = generator.determine_adr_status("**Status:** Accepted", {})

    assert status == "accepted"


def test_extract_adr_metadata_uses_superseded_bucket_when_relationship_requires_it() -> (
    None
):
    """Accepted ADRs with full supersession should not stay in accepted bucket."""
    generator = ADRRegistryGenerator()

    metadata = generator.extract_adr_metadata(
        Path("docs/02-architecture/decisions/ADR-003-in-memory-locking-strategy.md")
    )

    assert metadata is not None
    assert metadata.status == "superseded"
    assert metadata.source_status == "Superseded (revised 2025-12-23; see ADR-010)"


def test_extract_adr_metadata_recovers_decision_date_from_table_when_header_is_placeholder() -> (
    None
):
    """Decision-date extraction must survive placeholder inline header dates."""
    generator = ADRRegistryGenerator()

    metadata = generator.extract_adr_metadata(
        Path(
            "docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md"
        )
    )

    assert metadata is not None
    assert metadata.status == "accepted"
    assert metadata.decision_date == "2026-02-06"


def test_adr_033_explicitly_retires_silver_cross_field_runtime_executor() -> None:
    """ADR-033 must not leave the Silver cross-field executor as ambiguous debt."""
    adr_text = Path(
        "docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md"
    ).read_text(encoding="utf-8")

    assert "Level 2 Silver runtime executor is explicitly retired" in adr_text
    assert "must not be treated as an active implementation gap" in adr_text
