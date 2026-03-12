"""Unit tests for metadata_assemblers re-export module."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_metadata_assemblers_reexports() -> None:
    """composition.services.metadata_assemblers re-exports canonical classes."""
    from bioetl.composition.services.metadata_assemblers import (
        GoldMetadataAssembler,
        SilverMetadataAssembler,
    )

    assert GoldMetadataAssembler is not None
    assert SilverMetadataAssembler is not None
