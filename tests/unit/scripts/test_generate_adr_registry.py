"""Regression tests for ADR registry generation."""

from __future__ import annotations

from pathlib import Path

from scripts.generate_adr_registry import ADRRegistryGenerator


ADR_008_PATH = Path(
    "docs/02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md"
)


def test_extract_adr_metadata_reads_inline_status_date_and_owner() -> None:
    """Generated registry must honor explicit ADR metadata from source docs."""
    generator = ADRRegistryGenerator()

    metadata = generator.extract_adr_metadata(ADR_008_PATH)

    assert metadata is not None
    assert metadata.status == "superseded"
    assert metadata.decision_date == "2025-12-22"
    assert metadata.owner == "BioETL Team"


def test_determine_adr_status_maps_accepted_to_active_bucket() -> None:
    """Accepted ADRs belong to the active registry bucket."""
    generator = ADRRegistryGenerator()

    status = generator.determine_adr_status("**Status:** Accepted", {})

    assert status == "active"
