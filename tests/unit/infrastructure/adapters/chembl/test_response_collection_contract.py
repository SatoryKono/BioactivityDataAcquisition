"""Missing response collections must never become successful zero-record runs."""

import httpx
import pytest

from bioetl.domain.exceptions import ApiError
from bioetl.infrastructure.adapters.chembl._client_request_helpers import (
    process_chembl_response,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"error": "temporary failure"},
        {"target_components": None},
        {"target_components": [], "page_meta": {"next": "/next"}},
    ],
)
def test_invalid_collection_fails_instead_of_reporting_empty_success(payload):
    with pytest.raises(ApiError):
        process_chembl_response(
            response=httpx.Response(200, json=payload),
            entity_type="target_component",
            mapper=ChemblEntityMapper,
        )


def test_explicit_empty_collection_is_valid_empty():
    rows, more = process_chembl_response(
        response=httpx.Response(
            200,
            json={
                "target_components": [],
                "page_meta": {"total_count": 0, "next": None},
            },
        ),
        entity_type="target_component",
        mapper=ChemblEntityMapper,
    )
    assert rows == []
    assert more is False
