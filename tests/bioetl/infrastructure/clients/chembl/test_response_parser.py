from pydantic import ValidationError
import pytest

from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)


def test_parse_activities():
    parser = ChemblResponseParserImpl()
    response = {
        "activities": [
            {"activity_id": "1", "standard_flag": True},
            {"activity_id": "2", "standard_flag": False},
        ],
        "page_meta": {"limit": 20},
    }
    records = parser.parse(response)
    assert len(records) == 2
    assert isinstance(records[0], ActivityRawModel)
    assert records[0].activity_id == "1"


def test_parse_empty():
    parser = ChemblResponseParserImpl()
    response = {"page_meta": {}}
    records = parser.parse(response)
    assert records == []


def test_parse_invalid_payload():
    parser = ChemblResponseParserImpl()
    response = {"activities": [{"activity_id": 1}]}

    with pytest.raises(ValidationError):
        parser.parse(response)


def test_extract_metadata():
    parser = ChemblResponseParserImpl()
    response = {"page_meta": {"offset": 10}}
    meta = parser.extract_metadata(response)
    assert meta["offset"] == 10
