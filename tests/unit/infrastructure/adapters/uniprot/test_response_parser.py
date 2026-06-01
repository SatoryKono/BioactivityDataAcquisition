"""Tests for UniProt response parser helpers."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from bioetl.infrastructure.adapters.uniprot.response_parser import (
    parse_uniprot_protein_response,
)


pytestmark = pytest.mark.unit

def test_parse_uniprot_protein_response_returns_records_and_cursor() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [{"primaryAccession": "P12345"}],
        "nextCursor": "cursor-1",
    }

    assert parse_uniprot_protein_response(response) == (
        [{"primaryAccession": "P12345"}],
        "cursor-1",
    )


def test_parse_uniprot_protein_response_handles_malformed_payload() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = "bad-payload"

    assert parse_uniprot_protein_response(response) == ([], None)


def test_parse_uniprot_protein_response_filters_malformed_results_and_cursor() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [{"primaryAccession": "P12345"}, "bad-record", None],
        "nextCursor": 123,
    }

    assert parse_uniprot_protein_response(response) == (
        [{"primaryAccession": "P12345"}],
        None,
    )
