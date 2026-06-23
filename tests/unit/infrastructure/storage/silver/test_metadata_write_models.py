"""Focused branch tests for Silver metadata write request coercion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
    _coerce_silver_metadata_write_request,
)


pytestmark = pytest.mark.unit


def test_coerce_silver_metadata_write_request_returns_request_instance() -> None:
    request = _SilverMetadataWriteRequest(
        table_path="data/output/silver/chembl/activity",
        table_name="chembl.activity",
        records=[],
        primary_keys=["activity_id"],
        mode=SilverWriteMode.MERGE,
    )

    assert _coerce_silver_metadata_write_request(request) is request


def test_coerce_silver_metadata_write_request_rejects_mixed_request_styles() -> None:
    request = _SilverMetadataWriteRequest(
        table_path="path",
        table_name="table",
        records=[],
        primary_keys=[],
        mode=SilverWriteMode.MERGE,
    )

    with pytest.raises(TypeError, match="cannot be combined"):
        _coerce_silver_metadata_write_request(request, args=("extra",))


def test_coerce_silver_metadata_write_request_covers_legacy_errors() -> None:
    with pytest.raises(TypeError, match="too many positional arguments"):
        _coerce_silver_metadata_write_request(None, args=tuple(range(14)))

    with pytest.raises(TypeError, match="multiple values for argument 'table_path'"):
        _coerce_silver_metadata_write_request(
            "path",
            kwargs={
                "table_path": "duplicate",
                "table_name": "chembl.activity",
                "records": [],
                "primary_keys": [],
                "mode": SilverWriteMode.MERGE,
            },
        )

    with pytest.raises(TypeError, match="unexpected keyword arguments: extra"):
        _coerce_silver_metadata_write_request(
            None,
            kwargs={
                "table_path": "path",
                "table_name": "chembl.activity",
                "records": [],
                "primary_keys": [],
                "mode": SilverWriteMode.MERGE,
                "extra": "value",
            },
        )

    with pytest.raises(TypeError, match="missing required arguments: mode"):
        _coerce_silver_metadata_write_request(
            None,
            kwargs={
                "table_path": "path",
                "table_name": "chembl.activity",
                "records": [],
                "primary_keys": [],
            },
        )


def test_coerce_silver_metadata_write_request_builds_defaults_and_optional_fields() -> None:
    started_at = datetime(2026, 6, 17, tzinfo=UTC)

    request = _coerce_silver_metadata_write_request(
        "path",
        args=("chembl.activity", [], ["activity_id"], SilverWriteMode.MERGE),
        kwargs={"started_at": started_at, "version_after": 3},
    )

    assert request.table_path == "path"
    assert request.table_name == "chembl.activity"
    assert request.partition_by is None
    assert request.started_at is started_at
    assert request.version_after == 3

