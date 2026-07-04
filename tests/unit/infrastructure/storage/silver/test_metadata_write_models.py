"""Focused tests for Silver metadata write request models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver import metadata_operations
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)


pytestmark = pytest.mark.unit


def test_silver_metadata_write_request_defaults_and_optional_fields() -> None:
    started_at = datetime(2026, 6, 17, tzinfo=UTC)

    request = _SilverMetadataWriteRequest(
        table_path="path",
        table_name="chembl.activity",
        records=[],
        primary_keys=["activity_id"],
        mode=SilverWriteMode.MERGE,
        started_at=started_at,
        version_after=3,
    )

    assert request.table_path == "path"
    assert request.table_name == "chembl.activity"
    assert request.partition_by is None
    assert request.started_at is started_at
    assert request.version_after == 3


def test_silver_metadata_write_legacy_coercer_is_not_exported() -> None:
    assert not hasattr(metadata_operations, "_coerce_silver_metadata_write_request")
