"""Fail-closed argument contracts for canonical Silver write requests."""

from __future__ import annotations

from typing import cast

import pytest

from bioetl.domain.ports.storage.silver_port import (
    SilverWriteRequest,
    coerce_silver_write_request,
)
from bioetl.domain.types import ArrowSchema

pytestmark = pytest.mark.unit


def _required_kwargs() -> dict[str, object]:
    return {
        "table_name": "chembl.activity",
        "records": [],
        "primary_keys": ["activity_id"],
        "schema": cast(ArrowSchema, object()),
    }


def test_typed_request_rejects_mixed_legacy_arguments() -> None:
    """A typed request cannot be ambiguously combined with positional input."""
    request = SilverWriteRequest(
        table_name="chembl.activity",
        records=[],
        primary_keys=["activity_id"],
        schema=cast(ArrowSchema, object()),
    )

    with pytest.raises(TypeError, match="cannot be combined"):
        coerce_silver_write_request(request, args=("extra",))


def test_legacy_request_rejects_too_many_positional_arguments() -> None:
    """Legacy compatibility remains bounded to its declared positional shape."""
    with pytest.raises(TypeError, match="too many positional arguments"):
        coerce_silver_write_request(None, args=tuple(range(11)))


def test_legacy_request_rejects_duplicate_argument_ownership() -> None:
    """A field cannot be supplied through both positional and keyword forms."""
    with pytest.raises(TypeError, match="multiple values.*table_name"):
        coerce_silver_write_request(
            "chembl.activity",
            kwargs={"table_name": "pubchem.compound"},
        )


def test_legacy_request_rejects_unexpected_keyword() -> None:
    """Unknown fields fail before request construction instead of being ignored."""
    kwargs = _required_kwargs()
    kwargs["unsupported_option"] = True

    with pytest.raises(TypeError, match="unexpected keyword arguments"):
        coerce_silver_write_request(kwargs=kwargs)


def test_legacy_request_reports_all_missing_required_fields() -> None:
    """Missing required identity and data fields are reported explicitly."""
    with pytest.raises(TypeError, match="records, primary_keys, schema"):
        coerce_silver_write_request("chembl.activity")
