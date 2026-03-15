"""Unit tests for metadata_coordinator re-export module."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_metadata_coordinator_reexports() -> None:
    """composition.services.metadata_coordinator re-exports canonical class."""
    from bioetl.application.services.metadata_coordinator import (
        MetadataCoordinator as CanonicalMetadataCoordinator,
    )
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator

    assert MetadataCoordinator is CanonicalMetadataCoordinator
