"""Unit tests for lineage persistence helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.metadata_lineage_bundle import MetadataLineageBundle
from bioetl.domain.lineage import LineageGraphFragment
from bioetl.infrastructure.storage.lineage_persistence import (
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)


class _CoordinatorWithBundle:
    def __init__(self, metadata: object, fragment: LineageGraphFragment) -> None:
        self._metadata = metadata
        self._fragment = fragment

    def create_silver_metadata_bundle(self, input_data: object) -> MetadataLineageBundle:
        _ = input_data
        return MetadataLineageBundle(
            metadata=self._metadata,
            lineage_fragment=self._fragment,
        )

    def create_silver_metadata(self, input_data: object) -> object:
        _ = input_data
        return self._metadata


@pytest.mark.unit
def test_resolve_metadata_and_lineage_fragment_prefers_bundle_method() -> None:
    metadata = MagicMock()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        created_at=datetime.now(UTC),
    )
    coordinator = _CoordinatorWithBundle(metadata=metadata, fragment=fragment)

    resolved_metadata, resolved_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name="create_silver_metadata",
        input_data=object(),
        fallback_factory=MagicMock(return_value=MagicMock()),
    )

    assert resolved_metadata is metadata
    assert resolved_fragment == fragment


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_lineage_fragment_if_present_calls_store() -> None:
    fragment = LineageGraphFragment(
        fragment_id="gold:fragment-1",
        created_at=datetime.now(UTC),
    )
    store = MagicMock()

    await persist_lineage_fragment_if_present(
        lineage_store=store,
        lineage_fragment=fragment,
    )

    store.save.assert_called_once_with(fragment)

